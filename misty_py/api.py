from __future__ import annotations

import asyncio
import inspect
import textwrap
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
from typing import Dict, List, Any, Optional, Set, Union

import arrow
import requests

from .misty_ws import MistyWS, Sub, SubData
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
        self._ready_holder: asyncio.Event = None

    def __init_subclass__(cls, **kwargs):
        if not cls.__name__.startswith('_'):
            cls._registered_classes.add(cls)

    @property
    def _ready(self):
        """#TODO: do we need this here or can it just happen in regular, non-async __init__s"""
        if self._ready_holder is None:
            self._ready_holder = asyncio.Event()
        return self._ready_holder

    async def _get(self, endpoint, **params):
        return await self.api._get(endpoint, **params)

    async def _get_j(self, endpoint, **params) -> JSONObjOrObjs:
        return await self.api._get_j(endpoint, **params)

    async def _post(self, endpoint, json: Optional[dict] = None, **params):
        return await self.api._post(endpoint, json, **params)

    async def _delete(self, endpoint, json: Optional[dict] = None, **params):
        return await self.api._delete(endpoint, json, **params)


# ======================================================================================================================
# PartialAPIs
# ======================================================================================================================

class ImageAPI(PartialAPI):
    """handle pics, video, uploading/downloading images, changing led color, etc"""

    def __init__(self, api: MistyAPI):
        super().__init__(api)
        # TODO: add back in once we have misty
        # self.saved_images = asyncio.run(self.list())

    async def list(self) -> Dict[str, json_obj]:
        images = await self._get_j('images/list')
        res = self.saved_images = {i.name: i for i in images}
        return res

    async def get(self, file_name: str, *, as_base64: bool = True):
        # TODO:  test with as_base64 set to both True and False
        cor = self._get_j if as_base64 else self._get
        return await cor('images', FileName=file_name, Base64=as_base64)

    async def upload(self, file_name: str, width: Optional[int] = None, height: Optional[int] = None,
                     *, apply_immediately: bool = False, overwrite_existing: bool = True, as_byte_array: bool = False):
        if as_byte_array:
            raise ValueError('uploading `as_byte_array` is not currently supported')

        payload = json_obj(FileName=file_name, ImmediatelyApply=apply_immediately, OverwriteExisting=overwrite_existing)
        payload.add_if_not_none(Width=width, Height=height)

        return await self._post('images', payload)

    async def display(self, file_name: str, time_out_secs: float, alpha: float = 0.0):
        # TODO: validate image exists - upload if not?
        return await self._post('images/display', dict(FileName=file_name, TimeOutSeconds=time_out_secs, Alpha=alpha))

    async def set_led(self, rgb: RGB):
        rgb.validate()
        return await self._post('led', rgb.json)

    async def delete(self, file_name: str):
        return await self._delete('images', dict(FileName=file_name))

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
        return await self._post('video/record/start')

    async def stop_recording_video(self):
        return await self._post('video/record/stop')

    async def get_recorded_video(self):
        return await self._get_j('video')


class AudioAPI(PartialAPI):
    """record, play, change volume, manage audio files"""

    def __init__(self, api: MistyAPI):
        super().__init__(api)
        # TODO: add back in once we have misty
        # self.saved_audio = asyncio.run(self.list())

    async def get(self, file_name: str) -> Any:
        # TODO: what the hell do we get back?
        return await self._get_j('audio', FileName=file_name)

    async def list(self) -> Dict[str, json_obj]:
        audio = await self._get_j('audio/list')
        res = self.saved_audio = {a.name: a for a in audio}
        return res

    async def upload(self, file_name: str, *, as_byte_array: bool = False, apply_immediately: bool = False,
                     overwrite_existing: bool = True):
        if as_byte_array:
            raise ValueError('uploading `as_byte_array` is not currently supported')

        payload = dict(FileName=file_name, ImmediatelyApply=apply_immediately, OverwriteExisting=overwrite_existing)
        await self._post('audio', payload)

    async def play(self, file_name_or_id: str, volume: int = 100, *, as_file_name: bool = True):
        payload = dict(Volume=min(max(volume, 1), 100))
        payload['FileName' if as_file_name else 'AssetId'] = file_name_or_id
        await self._post('audio/play', payload)

    async def delete(self, file_name: str):
        await self._delete('audio', dict(FileName=file_name))

    async def set_default_volume(self, volume):
        await self._post('audio/volume', dict(Volume=min(max(volume, 0), 100)))

    async def start_recording(self, filename: str, how_long_secs: Optional[float] = None):
        fn = f'{filename.rstrip(".wav")}.wav'
        await self._post('audio/record/start', json_obj(FileName=fn))
        if how_long_secs is not None:
            how_long_secs = min(max(how_long_secs, 0), 60)
            if how_long_secs:
                await asyncio.sleep(how_long_secs)
                await self.stop_recording()

    async def stop_recording(self):
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
        sub_info = await self.api.ws.subscribe(Sub.face_recognition, self._process_face_message)

    async def stop_detection(self):
        """stop finding/detecting faces in misty's line of vision"""
        await self._post('faces/detection/stop')

    async def _process_face_message(self, sub_data: SubData):
        print(sub_data)

    async def start_training(self):
        """
        start training a particular face

        TODO: subscribe to FaceEvents to figure when done
        TODO: set up something to alert the user that this is happening
            - change LED colors, display some text
        """
        await self._post('faces/training/start')

    async def stop_training(self):
        """stop training a particular face"""
        await self._post('faces/training/stop')

    async def cancel_training(self):
        """shouldn't need to call unless you want to manually stop something in progress"""
        await self._get('faces/training/cancel')

    async def start_recognition(self):
        """start attempting to recognize faces"""
        await self._post('faces/recognition/start')

    async def stop_recognition(self):
        """stop attempting to recognize faces"""
        await self._post('faces/recognition/stop')


class MovementAPI(PartialAPI):
    """specifically control head, arms, driving movement, etc"""

    @staticmethod
    def _validate_vel_pct(**vel_pcts):
        fails = {name: val for name, val in vel_pcts.items()
                 if val is not None
                 and not -100 <= val <= 100}
        if fails:
            raise ValueError(f'invalid value for vel_pct: {fails}, must be in range [-100, 100] or `None`')

    async def drive(self, linear_vel_pct: int, angular_vel_pct: int, time_ms: Optional[int] = None):
        """
        angular_vel_pct: -100 is full speed clockwise, 100 is full speed counter-clockwise
        """
        self._validate_vel_pct(linear_vel_pct=linear_vel_pct, angular_vel_pct=angular_vel_pct)
        payload = json_obj.from_not_none(LinearVelocity=linear_vel_pct, AngularVelocity=angular_vel_pct)
        endpoint = 'drive'

        if time_ms:
            payload['TimeMS'] = time_ms
            endpoint += '/time'

        return await self._post(endpoint, payload)

    async def drive_track(self, left_track_vel_pct: float = 0.0, right_track_vel_pct: float = 0.0):
        """control drive tracks individually"""
        self._validate_vel_pct(left_track_vel_pct=left_track_vel_pct, right_track_vel_pct=right_track_vel_pct)
        return await self._post('drive/track',
                                dict(LeftTrackSpeed=left_track_vel_pct, RightTrackSpeed=right_track_vel_pct))

    async def move_arms(self, *arm_settings: ArmSettings):
        """pass either/both left and right arm settings"""
        payload = {k: v for arm in arm_settings for k, v in arm.json.items()}
        if payload:
            return await self._post('arms/set', payload)

    async def move_arms(self, l_position: Optional[float] = None, l_velocity: Optional[float] = None,
                        r_position: Optional[float] = None, r_velocity: Optional[float] = None):
        """pass either/both left and right arm settings"""
        arm_settings = (ArmSettings('left', l_position, l_velocity),
                        ArmSettings('right', r_position, r_velocity))
        payload = {k: v for arm in arm_settings for k, v in arm.json.items()}
        if payload:
            return await self._post('arms/set', payload)

    async def move_head(self, pitch: Optional[float] = None, roll: Optional[float] = None, yaw: Optional[float] = None):
        """
        all vals in range [-100, 100]

        pitch: up and down
        roll: tilt (ear to shoulder)
        yaw: turn left and right
        velocity: how quickly
        """
        return await self._post('head', HeadSettings(pitch, roll, yaw, 1).json)

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
        return await self._post('robot/halt')


class SystemAPI(PartialAPI):
    """
    interact with various system elements on the robot

    get logs, battery, etc
    """

    async def clear_error_msg(self):
        return await self._post('text/clear')

    @property
    async def networks(self):
        return await self._get_j('networks')
        # return [Wifi.from_misty(o) for o in await self._get_j('networks')]

    @property
    async def battery(self):
        return await self._get_j('battery')

    @property
    async def device_info(self):
        return await self._get_j('device')

    async def help(self, command: Optional[str] = None):
        return await self._get_j('help', **json_obj.from_not_none(command=command))

    async def get_logs(self):
        # TODO: implement individual date functionality
        return await self._get_j('logs')

    async def perform_system_update(self):
        return await self._post('system/update')

    async def set_wifi_network(self, name, password):
        payload = dict(NetworkName=name, Password=password)
        return await self._post('network', payload)

    async def send_to_backpack(self, msg: str):
        """not sure what kind of data/msg we can send - perhaps Base64 encode to send binary data?"""
        return await self._post('serial', dict(Message=msg))


class _SlamHelper(PartialAPI):
    """
    context manager to handle initializing and stopping slam functionality

    used by the NavigationAPI
    """

    def __init__(self, api: MistyAPI, endpoint: str):
        super().__init__(api)
        self._endpoint = endpoint
        self._num_current_slam_streams = 0

    async def _handler(self, sub_data: SubData):
        """set the `_ready` event after the sensors are ready"""
        # TODO: check if these are the same for all the slam types
        if sub_data.data.message.slamStatus.runMode == 'Exploring':
            self._ready.set()

    async def _start(self):
        await self._post(f'slam/{self._endpoint}/start')
        async with self.api.ws.sub_unsub(Sub.self_state, self._handler):
            await self._ready.wait()

    async def _stop(self):
        self._ready.clear()
        return await self._post(f'slam/{self._endpoint}/stop')

    async def __aenter__(self):
        self._num_current_slam_streams += 1
        if self._num_current_slam_streams == 1:
            await self._start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._num_current_slam_streams -= 1
        if self._num_current_slam_streams == 0:
            await self._stop()


class NavigationAPI(PartialAPI):
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
        return ','.join(map(str, coords))

    async def drive_to_coordinates(self, coords: Coords):
        async with self.slam_tracking:
            await self._post('drive/coordinates', dict(Destination=self._format_coords(coords)))

    async def follow_path(self, *coords: Coords):
        async with self.slam_tracking:
            if len(coords) == 1:
                return await self.drive_to_coordinates(*coords)
            return await self._post('drive/path', dict(Path=self._format_coords(*coords)))


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
        return await self._post('skills/start',
                                json_obj.from_not_none(Skill=skill_name_or_uid, Method=method)).json()['result']

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

    def __init__(self, ip):
        self.ip = ip
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

        self.subscription_data: Dict[Sub, SubData] = dict.fromkeys(Sub, SubData(arrow.Arrow.min, json_obj(), None))

    # ==================================================================================================================
    # REST CALLS
    # ==================================================================================================================
    def _endpoint(self, endpoint, **params) -> str:
        res = f'{self.ip}/api/{endpoint}'

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

    async def _get_j(self, endpoint, **params) -> JSONObjOrObjs:
        return json_obj((await self._get(endpoint, **params)).json()['result'])

    async def _post(self, endpoint, json: Optional[dict] = None, **params):
        return await self._request('POST', endpoint, **params, json=json)

    async def _delete(self, endpoint, json: Optional[dict] = None, **params):
        return await self._request('DELETE', endpoint, **params, json=json)


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
