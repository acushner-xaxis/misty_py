from __future__ import annotations

import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
from typing import Dict, List, Any, Type, TypeVar, Optional

import arrow
import requests

from misty_ws import MistyWS, Sub, SubscriptionInfo
from utils import *

# TODO:
# x Asset
# x Backpack
# x Event
# x Expression
# x Movement
# x Navigation
# x Perception
# Skill Management
# x System

WIDTH = 480
HEIGHT = 272
NAME = 'co-pi-lette'


# ======================================================================================================================
# ======================================================================================================================

async def delay(num_secs, coro):
    await asyncio.sleep(num_secs)
    await coro


class SubAPI(RestAPI):
    def __init__(self, api: MistyAPI):
        self._api = api

    async def _get(self, endpoint, **params):
        return await self._api._get(endpoint, **params)

    async def _get_j(self, endpoint, **params) -> Dict:
        return await self._api._get_j(endpoint, **params)

    async def _post(self, endpoint, json: Optional[dict] = None, **params):
        return await self._api._post(endpoint, json, **params)

    async def _delete(self, endpoint, json: Optional[dict] = None, **params):
        return await self._api._delete(endpoint, json, **params)


# ======================================================================================================================
# SubAPIs
# ======================================================================================================================

class ImageAPI(SubAPI):
    async def get(self, file_name: str, as_base64: bool = True) -> Image:
        # TODO:  test with as_base64 set to both True and False
        return Image.from_misty(await self._get_j('images', FileName=file_name, Base64=as_base64))

    async def list(self) -> Dict[str, Image]:
        images = (Image.from_misty(i) for i in await self._get_j('images/list'))
        return {i.name: i for i in images}

    async def upload(self, file_name: str, as_byte_array: bool = False, width: Optional[int] = None,
                     height: Optional[int] = None, apply_immediately: bool = False, overwrite: bool = True):
        if as_byte_array:
            raise ValueError('uploading `as_byte_array` is not currently supported')

        payload = dict(FileName=file_name, ImmediatelyApply=apply_immediately, OverwriteExisting=overwrite)
        if width:
            payload['Width'] = width
        if height:
            payload['Height'] = height

        await self._post('images', payload)

    async def display(self, file_name: str, time_out_secs: float, alpha: float):
        # TODO: validate image exists - upload if not?
        await self._post('images/display', dict(FileName=file_name, TimeOutSeconds=time_out_secs, Alpha=alpha))

    async def set_led(self, rgb: RGB):
        rgb.validate()
        await self._post('led', rgb.json)

    async def delete(self, file_name: str):
        await self._delete('images', dict(FileName=file_name))

    @staticmethod
    def _validate_take_picture(file_name, width, height, show_on_screen):
        if bool(width) + bool(height) == 1:
            raise ValueError("must supply both width and height, or neither. can't supply just one")

        if show_on_screen and not file_name:
            raise ValueError('in order for `show_on_screen` to work, you must provide a file_name')

    async def take_picture(self, file_name: Optional[str] = None, width: Optional[int] = None,
                           height: Optional[int] = None,
                           *, get_result: bool = True, show_on_screen: Optional[bool] = False,
                           overwrite_existing=True):
        self._validate_take_picture(file_name, width, height, show_on_screen)

        payload = json_obj.from_not_none(Base64=get_result, FileName=file_name, Width=width, Height=height,
                                         DisplayOnScreen=show_on_screen, OverwriteExisting=overwrite_existing)
        return await self._get_j('cameras/rgb', **payload)

    async def start_recording_video(self):
        """
        video is limited:
        - records up to 10 seconds
        - can only store one recording at a time
        """
        await self._post('video/record/start')

    async def stop_recording_video(self):
        await self._post('video/record/stop')

    async def get_recorded_video(self):
        return await self._get_j('video')


class AudioAPI(SubAPI):
    """record, play, change volume, manage audio files"""

    async def get(self, file_name: str) -> Any:
        # TODO: what the hell do we get back?
        return await self._get_j('audio', FileName=file_name)

    async def list(self) -> Dict[str, Audio]:
        audio = (Audio.from_misty(a) for a in await self._get_j('audio/list'))
        return {a.name: a for a in audio}

    async def upload(self, file_name: str, as_byte_array: bool = False, apply_immediately: bool = False,
                     overwrite: bool = True):
        if as_byte_array:
            raise ValueError('uploading `as_byte_array` is not currently supported')

        payload = dict(FileName=file_name, ImmediatelyApply=apply_immediately, OverwriteExisting=overwrite)
        await self._post('audio', payload)

    async def play(self, file_name_or_id: str, volume: int = 100, as_file_name: bool = True):
        payload = dict(Volume=min(max(volume, 1), 100))
        payload['FileName' if as_file_name else 'AssetId'] = file_name_or_id
        await self._post('audio/play', payload)

    async def delete(self, file_name: str):
        await self._delete('audio', dict(FileName=file_name))

    async def set_default_volume(self, volume):
        await self._post('audio/volume', dict(Volume=min(max(volume, 0), 100)))

    async def start_recording(self, filename: str, len_secs: Optional[int] = None):
        fn = f'{filename.rstrip(".wav")}.wav'
        await self._post('audio/record/start', json_obj(FileName=fn))
        if len_secs is not None:
            len_secs = min(max(len_secs, 0), 60)
            if len_secs:
                await delay(len_secs, self.stop_recording())

    async def stop_recording(self):
        await self._post('audio/record/stop')


class FaceAPI(SubAPI):
    """perform face detection, training, recognition; delete faces"""

    def __init__(self, api: MistyAPI):
        super().__init__(api)

    async def list(self) -> List[str]:
        return await self._get_j('faces')

    async def delete(self, *, name: Optional[str] = None, delete_all: bool = False):
        """rm faces from misty"""
        if bool(delete_all) + bool(name) != 1:
            raise ValueError('set exactly one of `name` or `delete_all`')

        kwargs = {}
        if name:
            kwargs['FaceId'] = name

        await self._delete('faces', **kwargs)

    async def start_detection(self):
        """
        start finding/detecting faces in misty's line of vision

        TODO: subscribe to FaceEvents to figure out when it's done?
        """
        await self._post('faces/detection/start')
        sub_info = await self._api.ws.subscribe(Sub.face_recognition, self._process_face_message)

    async def stop_detection(self):
        """stop finding/detecting faces in misty's line of vision"""
        await self._post('faces/detection/stop')

    async def _process_face_message(self, msg: json_obj, sub_info: SubscriptionInfo):
        print(msg)
        print(sub_info)

    async def start_training(self):
        """
        start training a particular face

        TODO: subscribe to FaceEvents to figure when done
        TODO: set up something to alert the user that this is happening
            - change LED colors, display some text
        """
        await self._post('faces/training/start')

    async def cancel_training(self):
        """shouldn't need to call unless you want to manually stop something in progress"""
        await self._get('faces/training/cancel')

    async def stop_training(self):
        """stop training a particular face"""
        await self._post('faces/training/stop')

    async def start_recognition(self):
        await self._post('faces/recognition/start')

    async def stop_recognition(self):
        """stop attempting to recognize faces"""
        await self._post('faces/recognition/stop')


class MovementAPI(SubAPI):
    """specifically control driving movement, head, arms, etc"""

    @staticmethod
    def _validate_vel_pct(**vel_pcts):
        fails = {}
        for name, val in vel_pcts.items():
            if not -100 <= val <= 100:
                fails[name] = val
        if fails:
            raise ValueError(f'invalid value for vel_pct: {fails}, must be in range [-100, 100]')

    async def drive(self, linear_vel_pct: int, angular_vel_pct: int):
        return await self.drive_time(linear_vel_pct, angular_vel_pct)

    async def drive_time(self, linear_vel_pct: int, angular_vel_pct: int, time_ms: Optional[int] = None):
        """
        angular_vel_pct: -100 is full speed clockwise, 100 is full speed counter-clockwise
        """
        self._validate_vel_pct(linear_vel_pct=linear_vel_pct, angular_vel_pct=angular_vel_pct)
        payload = dict(LinearVelocity=linear_vel_pct, AngularVelocity=angular_vel_pct)
        endpoint = 'drive'

        if time_ms:
            payload['TimeMS'] = time_ms
            endpoint += '/time'

        await self._post(endpoint, payload)

    async def drive_track(self, left_track_vel_pct: float = 0.0, right_track_vel_pct: float = 0.0):
        """control drive tracks individually"""
        self._validate_vel_pct(left_track_vel_pct=left_track_vel_pct, right_track_vel_pct=right_track_vel_pct)
        await self._post('drive/track', dict(LeftTrackSpeed=left_track_vel_pct, RightTrackSpeed=right_track_vel_pct))

    async def move_arms(self, *arm_settings: ArmSettings):
        """pass either/both left and right arm settings"""
        payload = {k: v for arm in arm_settings for k, v in arm.json.items()}
        if payload:
            await self._post('arms/set', payload)

    async def move_head(self, settings: HeadSettings):
        await self._post('head', settings.json)

    async def stop(self, *, everything=False):
        """
        stop motion

        if `everything` is set, will stop everything (i.e. halt)
        """
        if everything:
            return await self.halt()
        await self._post('drive/stop')

    async def halt(self):
        """stop everything"""
        await self._post('robot/halt')


class SystemAPI(SubAPI):
    """
    interact with various system elements on the robot

    get logs, battery, etc
    """

    async def clear_error_msg(self):
        await self._post('text/clear')

    @property
    async def networks(self) -> List[Wifi]:
        return [Wifi.from_misty(o) for o in await self._get_j('networks')]

    @property
    async def battery(self):
        return await self._get_j('battery')

    @property
    async def device_info(self):
        return await self._get_j('device')

    async def help(self, command: Optional[str] = None):
        params = json_obj.from_not_none(command=command)
        return await self._get_j('help', **params)

    async def get_logs(self):
        # TODO: implement individual date functionality
        return await self._get_j('logs')

    async def perform_system_update(self):
        await self._post('system/update')

    async def set_wifi_network(self, name, password):
        payload = dict(NetworkName=name, Password=password)
        await self._post('network', payload)

    async def send_to_backpack(self, msg: str):
        """not sure what kind of data/msg we can send - perhaps Base64 encode to send binary data?"""
        await self._post('serial', dict(Message=msg))


class _SlamHelper(SubAPI):
    """
    manage various slam functions on misty

    used by the NavigationAPI
    """

    def __init__(self, api: MistyAPI, endpoint: str):
        super().__init__(api)
        self._endpoint = endpoint
        self.num_current_slam_streams = 0

    async def start(self):
        return await self._post(f'slam/{self._endpoint}/start')

    async def stop(self):
        return await self._post(f'slam/{self._endpoint}/stop')

    async def __aenter__(self):
        self.num_current_slam_streams += 1
        if self.num_current_slam_streams == 1:
            await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.num_current_slam_streams -= 1
        if self.num_current_slam_streams == 0:
            await self.stop()


class NavigationAPI(SubAPI):
    """
    control mapping, tracking, driving, etc

    can also take depth/fisheye pics
    """

    def __init__(self, api: MistyAPI):
        super().__init__(api)
        self.slam_streaming = _SlamHelper(api, 'streaming')
        self.slam_mapping = _SlamHelper(api, 'map')
        self.slam_tracking = _SlamHelper(api, 'track')

    async def reset_slam(self):
        return await self._post('slam/reset')

    async def take_depth_pic(self):
        async with self.slam_streaming:
            return await self._get_j('cameras/depth')

    async def take_fisheye_pic(self):
        async with self.slam_streaming:
            return await self._get_j('cameras/fisheye')

    async def get_map(self):
        async with self.slam_mapping:
            return await self._get_j('slam/map')

    @staticmethod
    def _format_coords(*coords: Coords):
        return ','.join(f'{c.x}:{c.y}' for c in coords)

    async def drive_to_coordinates(self, coords: Coords):
        async with self.slam_tracking:
            await self._post('drive/coordinates', dict(Destination=self._format_coords(coords)))

    async def follow_path(self, *coords: Coords):
        async with self.slam_tracking:
            if len(coords) == 1:
                return await self.drive_to_coordinates(*coords)
            return await self._post('drive/path', dict(Path=self._format_coords(*coords)))


class SkillAPI(SubAPI):
    """interact with skills available on misty"""

    async def stop(self, skill_name: Optional[str] = None):
        await self._post('skills/cancel', json_obj.from_not_none(Skill=skill_name))

    async def delete(self, skill_uid: str):
        await self._delete(Skill=skill_uid)

    async def get_running(self):
        return [Skill.from_misty(s) for s in await self._get_j('skills/running')]

    async def get(self):
        return await self._get_j('skills')

    async def run(self, skill_name_or_uid, method: Optional[str] = None):
        return await self._post('skills/start',
                                json_obj.from_not_none(Skill=skill_name_or_uid, Method=method)).json()['result']

    async def save(self, zip_file_name: str, apply_immediately: bool = False, overwrite_existing: bool = True):
        await self._post('skills', dict(File=zip_file_name, ImmediatelyApply=apply_immediately,
                                        OverwriteExisting=overwrite_existing))

    async def trigger_skill_event(self, skill_uid: str, event_name: str, json: Optional[Dict] = None):
        """send an event to a currently running skill"""
        payload = json_obj.from_not_none(UniqueId=skill_uid, EventName=event_name, Payload=json)
        await self._post('skills/event', payload)


# ======================================================================================================================


class MistyAPI(RestAPI):
    _pool = ThreadPoolExecutor(16)

    def __init__(self, ip):
        self.ip = ip
        self.ws = MistyWS(ip)

        # ==================================================================================================================
        # APIs
        # ==================================================================================================================

        self.images = ImageAPI(self)
        self.audio = AudioAPI(self)
        self.faces = FaceAPI(self)
        self.movement = MovementAPI(self)
        self.system = SystemAPI(self)
        self.navigation = NavigationAPI(self)
        self.skills = SkillAPI(self)

    # ==================================================================================================================
    # REST CALLS
    # ==================================================================================================================
    def _endpoint(self, endpoint, **params) -> str:
        res = f'http://{self.ip}/api/{endpoint}'

        if params:
            param_str = '&'.join(f'{k}={v}' for k, v in params.items())
            res = f'{res}?{param_str}'

        return res

    async def _request(self, method, endpoint, json=None, **params):
        kwargs = json_obj.from_not_none(json=json)
        f = partial(requests.request, method, self._endpoint(endpoint, **params), **kwargs)
        return await asyncio.get_running_loop().run_in_executor(self._pool, f)

    async def _get(self, endpoint, **params):
        return await self._request('GET', endpoint, **params)

    async def _get_j(self, endpoint, **params) -> Dict:
        return await self._get(endpoint, **params).json()['result']

    async def _post(self, endpoint, json: Optional[dict] = None, **params):
        return await self._request('POST', endpoint, **params, json=json)

    async def _delete(self, endpoint, json: Optional[dict] = None, **params):
        return await self._request('DELETE', endpoint, **params, json=json)
