from __future__ import annotations

import asyncio
import inspect
import textwrap
import os
from abc import ABC, abstractmethod
from base64 import b64encode
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
from typing import Dict, Optional, Set, NamedTuple

from PIL import Image as PImage
from io import BytesIO

import arrow
import requests

from .misty_ws import MistyWS
from misty_py.subscriptions import SubType, SubPayload, EventCallback, Sub
from .utils import *

WIDTH = 480
HEIGHT = 272


# ======================================================================================================================
# ======================================================================================================================


# noinspection PyProtectedMember
class PartialAPI(RestAPI):
    """
    represent part of the overall api

    separate out methods into logical groups such as face, image, audio, etc
    """
    _registered_classes = set()  # only used for MistyAPI's __doc__

    def __init__(self, api: MistyAPI):
        self.api = api

    def __init_subclass__(cls, **kwargs):
        if not cls.__name__.startswith('_'):
            cls._registered_classes.add(cls)

    async def _get(self, endpoint, *, _headers=None, **params):
        return await self.api._get(endpoint, _headers=_headers, **params)

    async def _get_j(self, endpoint, *, _headers=None, **params) -> JSONObjOrObjs:
        return await self.api._get_j(endpoint, _headers=_headers, **params)

    async def _post(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        return await self.api._post(endpoint, json, _headers=_headers, **params)

    async def _delete(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        return await self.api._delete(endpoint, json, _headers=_headers, **params)


# ======================================================================================================================
# PartialAPIs
# ======================================================================================================================


class ImageAPI(PartialAPI):
    """handle pics, video, uploading/downloading images, changing led color, etc"""

    def __init__(self, api: MistyAPI):
        super().__init__(api)
        # TODO: add back in once we have misty
        # self.saved_images = asyncio.run(self.list())

    @staticmethod
    def save_image_locally(path, data: BytesIO):
        save_data_locally(path, data, '.jpg')

    @staticmethod
    def save_video_locally(path, data: BytesIO):
        save_data_locally(path, data, '.mov')

    async def list(self) -> Dict[str, json_obj]:
        """
        get images available on device as dict(name=json)
        store in `self.saved_images`
        return dict
        """
        images = await self._get_j('images/list')
        res = self.saved_images = json_obj((i.name, i) for i in images)
        return res

    async def get(self, file_name: str, *, as_base64: bool = False, display=True) -> BytesIO:
        """
        default to using binary data - decoding base64 is annoying
        default to displaying the image as well
        """
        cor = self._get_j if as_base64 else self._get
        res = await cor('images', FileName=file_name, Base64=as_base64)
        res = BytesIO(res.content)
        if display:
            PImage.open(res)
        return res

    async def upload(self, file_name: str, width: Optional[int] = None, height: Optional[int] = None,
                     *, apply_immediately: bool = False, overwrite_existing: bool = True):
        """upload a local image to misty"""
        payload = generate_upload_payload(file_name, apply_immediately, overwrite_existing)
        payload.add_if_not_none(Width=width, Height=height)
        return await self._post('images', payload)

    async def display(self, file_name: str, time_out_secs: Optional[float] = None, alpha: float = 1.0):
        """
        file_name: name on device
        time_out_secs: no idea what this does. seems to have no effect
        alpha: should be between 0 (totally transparent) and 1 (totally opaque), inclusive
        """
        return await self._post('images/display', dict(FileName=file_name, TimeOutSeconds=time_out_secs, Alpha=alpha))

    async def set_led(self, rgb: RGB = RGB(0, 0, 0)):
        """
        change color of torso's led
        use `RGB(0, 0, 0)` to turn led off
        """
        rgb.validate()
        return await self._post('led', rgb.json)

    async def delete(self, file_name: str):
        return await self._delete('images', dict(FileName=file_name))

    @staticmethod
    def _validate_take_picture(file_name, width, height, show_on_screen):
        if bool(width) + bool(height) == 1:
            raise ValueError("must supply either both width and height, or neither. can't supply just one")

        if show_on_screen and not file_name:
            raise ValueError('in order for `show_on_screen` to work, you must provide a file_name')

    async def take_picture(self, file_name: Optional[str] = None, width: Optional[int] = None,
                           height: Optional[int] = None,
                           *, get_result: bool = True, show_on_screen: Optional[bool] = False,
                           overwrite_existing=True):
        """
        if height is supplied, so must be width, and vice versa
        if you want to display on the screen, you must provide a filename

        # TODO: better way return data? maybe return a BytesIO instead of the actual base64 values returned
        """
        self._validate_take_picture(file_name, width, height, show_on_screen)

        payload = json_obj.from_not_none(Base64=get_result, FileName=file_name, Width=width, Height=height,
                                         DisplayOnScreen=show_on_screen, OverwriteExisting=overwrite_existing)
        return await self._get_j('cameras/rgb', **payload)

    async def start_recording_video(self, how_long_secs: Optional[int] = None):
        """
        video is limited:
        - record up to 10 seconds
        - can only store one recording at a time
        """
        res = await self._post('video/record/start')
        if how_long_secs:
            how_long_secs = min(max(1, how_long_secs), 10)
            asyncio.create_task(delay(how_long_secs, self.stop_recording_video()))
        return res

    async def stop_recording_video(self):
        return await self._post('video/record/stop')

    async def get_recorded_video(self) -> BytesIO:
        res = await self._get('video')
        return BytesIO(res.content)


class AudioAPI(PartialAPI):
    """record, play, change volume, manage audio files"""

    def __init__(self, api: MistyAPI):
        super().__init__(api)
        # TODO: add back in once we have misty
        # self.saved_audio = asyncio.run(self.list())

    async def get(self, file_name: str) -> BytesIO:
        # TODO: what the hell do we get back?
        res = await self._get('audio', FileName=file_name)
        return BytesIO(res.content)

    async def list(self) -> Dict[str, json_obj]:
        """
        get audio metadata available on device as dict(name=json)
        store in `self.saved_audio`
        return dict
        """
        audio = await self._get_j('audio/list')
        res = self.saved_audio = json_obj((a.name, a) for a in audio)
        return res

    async def upload(self, file_name: str, *, apply_immediately: bool = False, overwrite_existing: bool = True):
        """upload data (mp3, wav, not sure what else) to misty"""
        return await self._post('audio', generate_upload_payload(file_name, apply_immediately, overwrite_existing))

    async def _handle_how_long_secs(self, how_long_secs, blocking):
        if how_long_secs is not None:
            coro = delay(how_long_secs, self.stop_playing())
            if blocking:
                await coro
            else:
                asyncio.create_task(coro)
        elif blocking:
            # TODO: use metadata from audio_play_complete to make sure the correct sound is ending
            async def _wait_one(_):
                return True

            event = EventCallback(_wait_one)
            async with self.api.ws.sub_unsub(SubType.audio_play_complete, event):
                await event

    async def play(self, file_name: str, volume: int = 100, how_long_secs: Optional[int] = None, *, blocking=False):
        """play for how long you want to"""
        payload = dict(FileName=file_name, Volume=min(max(volume, 1), 100))
        res = await self._post('audio/play', payload)
        await self._handle_how_long_secs(how_long_secs, blocking)
        return res

    async def stop_playing(self):
        """trigger a small amount of silence to stop a playing song"""
        return await self.play('silence_stop.mp3')

    async def delete(self, file_name: str):
        return await self._delete('audio', dict(FileName=file_name))

    async def set_default_volume(self, volume):
        return await self._post('audio/volume', dict(Volume=min(max(volume, 0), 100)))

    async def start_recording(self, filename: str, how_long_secs: Optional[float] = None):
        """record audio"""
        fn = f'{filename.rstrip(".wav")}.wav'
        res = await self._post('audio/record/start', json_obj(FileName=fn))
        if how_long_secs is not None:
            how_long_secs = min(max(how_long_secs, 0), 60)
            if how_long_secs:
                asyncio.create_task(delay(how_long_secs, self.stop_recording()))
        return res

    async def stop_recording(self):
        """stop recording audio"""
        await self._post('audio/record/stop')


class FaceAPI(PartialAPI):
    """perform face detection, training, recognition; delete faces"""

    def __init__(self, api: MistyAPI):
        super().__init__(api)
        # TODO: add back in once we have misty
        # self.saved_faces = asyncio.run(self.list())

    async def list(self) -> Set[str]:
        res = self.saved_faces = set(await self._get_j('faces'))
        return res

    async def delete(self, *, name: Optional[str] = None, delete_all: bool = False):
        """rm faces from misty"""
        if bool(delete_all) + bool(name) != 1:
            raise ValueError('set exactly one of `name` or `delete_all`')

        await self._delete('faces', **(dict(FaceId=name) if name else {}))

    async def start_detection(self):
        """
        start finding/detecting faces in misty's line of vision

        TODO: subscribe to FaceEvents to figure out when it's done?
        """
        await self._post('faces/detection/start')

    async def stop_detection(self):
        """stop finding/detecting faces in misty's line of vision"""
        await self._post('faces/detection/stop')

    async def start_training(self, face_id: str):
        """
        start training a particular face

        TODO: subscribe to FaceEvents to figure when done
        TODO: set up something to alert the user that this is happening
            - change LED colors, display some text
        """
        return await self._post('faces/training/start', dict(FaceId=face_id))

    async def stop_training(self):
        """stop training a particular face"""
        return await self._post('faces/training/stop')

    async def cancel_training(self):
        """shouldn't need to call unless you want to manually stop something in progress"""
        return await self._get('faces/training/cancel')

    async def start_recognition(self):
        """start attempting to recognize faces"""
        return await self._post('faces/recognition/start')

    async def stop_recognition(self):
        """stop attempting to recognize faces"""
        return await self._post('faces/recognition/stop')

    async def start_key_phrase_recognition(self):
        # TODO: this
        raise NotImplementedError

    async def stop_key_phrase_recognition(self):
        # TODO: this
        raise NotImplementedError

    async def stop_all(self):
        return await asyncio.gather(self.stop_training(), self.cancel_training(), self.stop_recognition())


class MovementAPI(PartialAPI):
    """specifically control head, arms, driving movement, etc"""

    @staticmethod
    def _validate_vel_pct(**vel_pcts):
        fails = {name: val for name, val in vel_pcts.items()
                 if val is not None
                 and not -100 <= val <= 100}
        if fails:
            raise ValueError(f'invalid value for vel_pct: {fails}, must be in range [-100, 100] or `None`')

    async def drive(self, linear_vel_pct: int = 0, angular_vel_pct: int = 0, time_ms: Optional[int] = None):
        """
        angular_vel_pct: -100 is full speed counter-clockwise, 100 is full speed clockwise
        """
        angular_vel_pct *= -1
        self._validate_vel_pct(linear_vel_pct=linear_vel_pct, angular_vel_pct=angular_vel_pct)
        payload = json_obj.from_not_none(LinearVelocity=linear_vel_pct, AngularVelocity=angular_vel_pct)
        endpoint = 'drive'

        if time_ms:
            payload['TimeMS'] = time_ms
            endpoint += '/time'

        return await self._post(endpoint, payload)

    async def drive_track(self, left_track_vel_pct: int = 0, right_track_vel_pct: int = 0):
        """control drive tracks individually"""
        self._validate_vel_pct(left_track_vel_pct=left_track_vel_pct, right_track_vel_pct=right_track_vel_pct)
        return await self._post('drive/track',
                                dict(LeftTrackSpeed=left_track_vel_pct, RightTrackSpeed=right_track_vel_pct))

    async def move_arms(self, l_position: Optional[float] = None, l_velocity: Optional[float] = None,
                        r_position: Optional[float] = None, r_velocity: Optional[float] = None):
        """pass either/both left and right arm settings"""
        arm_settings = (ArmSettings('left', l_position, l_velocity),
                        ArmSettings('right', r_position, r_velocity))
        payload = {k: v for arm in arm_settings for k, v in arm.json.items()}
        if payload:
            return await self._post('arms/set', payload)

    async def move_head(self, pitch: Optional[float] = None, roll: Optional[float] = None, yaw: Optional[float] = None,
                        velocity: Optional[float] = None):
        """
        all vals in range [-100, 100]

        pitch: up and down
        roll: tilt (ear to shoulder)
        yaw: turn left and right
        velocity: how quickly
        """
        return await self._post('head', HeadSettings(pitch, roll, yaw, velocity).json)

    async def stop(self, *, everything=False):
        """
        stop motion

        if `everything` is set, will stop everything (i.e. halt)
        """
        if everything:
            return await self.halt()
        return await self._post('drive/stop')

    async def halt(self):
        """stop everything"""
        return await self._post('halt')

    async def drive_arc(self, heading_degrees: float, radius_m: float, time_ms: float, *, reverse: bool = False):
        payload = json_obj(Heading=heading_degrees * -1, Radius=radius_m, TimeMs=time_ms, Reverse=reverse)
        return await self._post('drive/arc', payload)


class BatteryInfo(NamedTuple):
    percent: float
    metadata: json_obj

    @classmethod
    def from_meta(cls, data):
        return cls(data.chargePercent * 100, data)


class SystemAPI(PartialAPI):
    """
    interact with various system elements on the robot

    get logs, battery, etc
    """

    async def clear_display_text(self):
        return await self._post('text/clear')

    @property
    async def wifi(self) -> Dict[str, str]:
        networks = await self._get_j('networks')
        return {n.ssid: n for n in networks}

    async def connect_wifi(self, ssid):
        """connect to known wifi"""
        return await self._post('networks', json_obj(NetworkId=ssid))

    async def set_wifi_network(self, name, password):
        """set up with username and password"""
        payload = dict(NetworkName=name, Password=password)
        return await self._post('network', payload)

    async def forget_wifi(self, ssid):
        return await self._delete('networks', json_obj(NetworkId=ssid))

    async def scan_wifi(self):
        """find available wifi networks"""
        return await self._get_j('networks/scan')

    @property
    async def battery_info(self) -> BatteryInfo:
        return BatteryInfo.from_meta(await self._get_j('battery'))

    @property
    async def device_info(self):
        return await self._get_j('device')

    async def help(self, endpoint: Optional[str] = None):
        """specs for the system at large"""
        return await self._get_j('help', **json_obj.from_not_none(command=endpoint))

    async def get_logs(self, date: arrow.Arrow = arrow.now()) -> str:
        params = json_obj()
        if date:
            params.date = date.format('YYYY/MM/DD')
        return (await self._get('logs', **params)).json()['result']

    @property
    async def log_level(self) -> str:
        return (await self._get('logs/level')).json()['result']

    async def set_log_level(self, log_level: str):
        return await self._post('logs/level', json_obj(LogLevel=log_level))

    @property
    async def is_update_available(self) -> bool:
        return (await self._get('system/updates')).json()['result']

    async def perform_system_update(self):
        return await self._post('system/update')

    async def get_websocket_names(self, class_name: Optional[str] = None):
        """specs for websocket api"""
        params = json_obj()
        if class_name:
            params.websocketClass = class_name
        return await self._get_j('websockets', **params)

    @property
    async def websocket_version(self):
        return (await self._get('websocket/version')).json()['result']

    async def send_to_backpack(self, msg: str):
        """not sure what kind of data/msg we can send - perhaps Base64 encode to send binary data?"""
        return await self._post('serial', dict(Message=msg))

    async def set_flashlight(self, on: bool = True):
        return await self._post('flashlight', dict(On=on))

    async def reboot(self, core=True, sensory_services=True):
        return await self._post('reboot', json_obj(Core=core, SensoryServices=sensory_services))


class _SlamHelper(PartialAPI, ABC):
    """
    context manager to handle initializing and stopping slam functionality

    used by the NavigationAPI
    """

    def __init__(self, api: MistyAPI, endpoint: str, timeout_secs=15.0):
        super().__init__(api)
        self._endpoint = endpoint
        self._num_current_slam_streams = 0
        self._ready_cb = EventCallback(self._sensor_ready, timeout_secs)
        self._off_cb = EventCallback(self._sensor_off, timeout_secs)

    @abstractmethod
    async def _sensor_ready(self, sp: SubPayload):
        """handler func that indicates when the sensor is ready"""

    async def _sensor_off(self, sp: SubPayload):
        """handler func that indicates when the sensor off"""
        return not await self._sensor_ready(sp)

    async def start(self):
        self._ready_cb.clear()
        await self._post(f'slam/{self._endpoint}/start')

    async def stop(self):
        self._off_cb.clear()
        return await self._post(f'slam/{self._endpoint}/stop')

    async def reset(self):
        return await self._post('slam/reset')

    async def __aenter__(self):
        self._num_current_slam_streams += 1
        if self._num_current_slam_streams == 1:
            await self.start()
            async with self.api.ws.sub_unsub(SubType.self_state, self._ready_cb):
                await self._ready_cb

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._num_current_slam_streams -= 1
        if self._num_current_slam_streams == 0:
            await self.stop()


class _SlamMapping(_SlamHelper):
    def __init__(self, api: MistyAPI):
        super().__init__(api, 'map')

    async def _sensor_ready(self, sp: SubPayload):
        ss = sp.data.message.slamStatus
        return (ss.runMode == 'Exploring'
                and all(v in ss.statusList for v in 'Ready Exploring HasPose Streaming'.split()))


class _SlamStreaming(_SlamHelper):
    def __init__(self, api: MistyAPI):
        super().__init__(api, 'streaming')

    async def _sensor_ready(self, sp: SubPayload):
        ss = sp.data.message.slamStatus
        return all(v in ss.statusList for v in 'Ready Streaming'.split())


class _SlamTracking(_SlamHelper):
    def __init__(self, api: MistyAPI):
        super().__init__(api, 'track')

    async def _sensor_ready(self, sp: SubPayload):
        ss = sp.data.message.slamStatus
        return (ss.runMode == 'Tracking'
                and all(v in ss.statusList for v in ('Ready', 'Tracking', 'HasPose', 'Streaming')))


class NavigationAPI(PartialAPI):
    """
    control mapping, tracking, driving, etc

    can also take depth/fisheye pics
    """

    def __init__(self, api: MistyAPI):
        super().__init__(api)
        self.slam_streaming = _SlamStreaming(api)
        self.slam_mapping = _SlamMapping(api)
        self.slam_tracking = _SlamTracking(api)

    async def reset_slam(self):
        return await self._post('slam/reset')

    async def take_depth_pic(self):
        async with self.slam_streaming:
            return await self._get_j('cameras/depth')

    async def take_fisheye_pic(self) -> BytesIO:
        async with self.slam_streaming:
            res = await self._get('cameras/fisheye')
            return BytesIO(res.content)

    async def get_map(self):
        return await self._get_j('slam/map')

    async def map(self):
        """# algo for misty to move around slowly mapping her environment"""
        # TODO: implement
        raise NotImplementedError

    async def drive_to_coordinates(self, coords: Coords):
        async with self.slam_tracking:
            await self._post('drive/coordinates', dict(Destination=Coords.format(coords)))

    async def follow_path(self, *coords: Coords):
        async with self.slam_tracking:
            if len(coords) == 1:
                return await self.drive_to_coordinates(*coords)
            return await self._post('drive/path', dict(Path=Coords.format(*coords)))


class SkillAPI(PartialAPI):
    """interact with on-robot skills available on misty"""

    async def stop(self, skill_name: Optional[str] = None):
        await self._post('skills/cancel', json_obj.from_not_none(Skill=skill_name))

    async def delete(self, skill_uid: str):
        await self._delete('skills', Skill=skill_uid)

    async def get_running(self):
        return await self._get_j('skills/running')

    async def get(self):
        return await self._get_j('skills')

    async def run(self, skill_name_or_uid, method: Optional[str] = None):
        return (await self._post('skills/start',
                                 json_obj.from_not_none(Skill=skill_name_or_uid, Method=method))).json()['result']

    async def save(self, zip_file_name: str, *, apply_immediately: bool = False, overwrite_existing: bool = True):
        await self._post('skills', dict(File=zip_file_name, ImmediatelyApply=apply_immediately,
                                        OverwriteExisting=overwrite_existing))

    async def trigger_skill_event(self, skill_uid: str, event_name: str, json: Optional[Dict] = None):
        """send an event to a currently running skill"""
        payload = json_obj.from_not_none(UniqueId=skill_uid, EventName=event_name, Payload=json)
        await self._post('skills/event', payload)


# ======================================================================================================================


class MistyAPI(RestAPI):
    """
    asyncio-based REST API for the misty II robot

    - wrap multiple `PartialAPI` objects to access misty
        - for organizational ease
    - handle interacting with websockets
    - a simple usage example

    ==========PartialAPIs============

    {partial_api_section}
    =================================


    ===========websockets============

        `ws` contains access to the websocket interface, used for pub/sub interaction

        `subscription_data` contains the most recent piece of data received from websockets

    =================================



    ==============usage==============

        {usage_section}

    =================================
    """

    _pool = ThreadPoolExecutor(16)

    def __init__(self, ip: Optional[str] = None):
        """either pass in ip directly or set in env"""
        self.ip = self._init_ip(ip)
        self.ws = MistyWS(self)

        # ==============================================================================================================
        # PartialAPIs
        # ==============================================================================================================

        self.images = ImageAPI(self)
        self.audio = AudioAPI(self)
        self.faces = FaceAPI(self)
        self.movement = MovementAPI(self)
        self.system = SystemAPI(self)
        self.navigation = NavigationAPI(self)
        self.skills = SkillAPI(self)

        # ==============================================================================================================
        # SUBSCRIPTION DATA - store most recent subscription info here
        # ==============================================================================================================

        self.subscription_data: Dict[Sub, SubPayload] = {}

    @staticmethod
    def _init_ip(ip):
        ip = ip or os.environ.get('MISTY_IP')
        if not ip:
            raise ValueError('You must provide an ip argument, or set $MISTY_IP in your env')

        if not ip.startswith('http://') or ip.startswith('https://'):
            ip = f'http://{ip}'
        return ip

    # ==================================================================================================================
    # REST CALLS
    # ==================================================================================================================
    def _endpoint(self, endpoint, **params) -> str:
        res = f'{self.ip}/api/{endpoint}'

        if params:
            param_str = '&'.join(f'{k}={v}' for k, v in params.items())
            res = f'{res}?{param_str}'

        return res

    async def _request(self, method, endpoint, json=None, *, _headers: Optional[Dict[str, str]] = None, **params):
        req_kwargs = json_obj.from_not_none(json=json, headers=_headers)
        f = partial(requests.request, method, self._endpoint(endpoint, **params), **req_kwargs)
        print(method, self._endpoint(endpoint, **params), _headers)
        return await asyncio.get_running_loop().run_in_executor(self._pool, f)

    async def _get(self, endpoint, *, _headers=None, **params):
        return await self._request('GET', endpoint, **params, _headers=_headers)

    async def _get_j(self, endpoint, *, _headers=None, **params) -> JSONObjOrObjs:
        return json_obj((await self._get(endpoint, **params, _headers=_headers)).json()['result'])

    async def _post(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        return await self._request('POST', endpoint, **params, json=json, _headers=_headers)

    async def _delete(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        return await self._request('DELETE', endpoint, **params, json=json, _headers=_headers)


def _run_example():
    """
    example function showing how misty can be used

    in addition, async funcs can be awaited directly from the jupyter console
    """

    async def run(ip):
        api = MistyAPI(ip)

        # run a single task and wait for it to be triggered
        post_res = await api.movement.drive(0, -20, 10000)

        # dispatch multiple tasks at once
        coros = (api.images.take_picture(),
                 api.system.help(),
                 api.system.battery  # note: `battery` is an "async" property
                 )
        results_in_order = await asyncio.gather(*coros)
        return results_in_order

    asyncio.run(run('https://fake'))


def _create_api_doc():
    """create part of MistyAPI docstring from code"""

    def _fmt_cls_doc(cls):
        d = '\n\t'.join(textwrap.dedent((cls.__doc__ or '')).strip().split('\n'))
        return f'{cls.__name__}: \n\t{d}\n\n'

    res = '\n'.join(map(_fmt_cls_doc, PartialAPI._registered_classes))
    return '\t' + '\n\t'.join(res.splitlines())


MistyAPI.__doc__ = MistyAPI.__doc__.format(partial_api_section=_create_api_doc(),
                                           usage_section='\n    '.join(inspect.getsource(_run_example).splitlines()))
help(MistyAPI)
