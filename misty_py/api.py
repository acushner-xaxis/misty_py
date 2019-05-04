from __future__ import annotations

from typing import List, Any, Type, TypeVar

import requests

from .color import RGB
from .datastructures import *

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

class SubAPI(RestAPI):
    def __init__(self, api: MistyAPI):
        self._api = api

    def _get(self, endpoint, **params):
        return self._api._get(endpoint, **params)

    def _get_j(self, endpoint, **params) -> Dict:
        return self._api._get_j(endpoint, **params)

    def _post(self, endpoint, json: Optional[dict] = None, **params):
        return self._api._post(endpoint, json, **params)

    def _delete(self, endpoint, json: Optional[dict] = None, **params):
        return self._api._delete(endpoint, json, **params)


T = TypeVar('T', bound=SubAPI)


class APIDescriptor:
    """
    only instantiate SubAPIs when accessed for the first time

    the SubAPIs must be annotated so this descriptor knows which type to instantiate

    once instantiated, it overwrites itself with the instance
    """

    def __set_name__(self, cls, name):
        self.name = name
        self.api_type = cls.__annotations__[name]

    def __get__(self, instance: T, cls: Type[T]) -> T:
        if not instance:
            return self

        res = self.__dict__[self.name] = self.api_type(instance._api)
        return res


# ======================================================================================================================
# SubAPIs
# ======================================================================================================================

class ImageAPI(SubAPI):
    def __init__(self, api: MistyAPI):
        super().__init__(api)
        self.images = self.list()

    def get(self, file_name: str, as_base64: bool = True) -> Image:
        # TODO:  test with as_base64 set to both True and False
        return Image.from_misty(self._get_j('images', FileName=file_name, Base64=as_base64))

    def list(self) -> Dict[str, Image]:
        images = (Image.from_misty(i) for i in self._get_j('images/list'))
        return {i.name: i for i in images}

    def upload(self, file_name: str, as_byte_array: bool = False, width: Optional[int] = None,
               height: Optional[int] = None, apply_immediately: bool = False, overwrite: bool = True):
        if as_byte_array:
            raise ValueError('uploading `as_byte_array` is not currently supported')

        payload = dict(FileName=file_name, ImmediatelyApply=apply_immediately, OverwriteExisting=overwrite)
        if width:
            payload['Width'] = width
        if height:
            payload['Height'] = height

        self._post('images', payload)

    def display(self, file_name: str, time_out_secs: float, alpha: float):
        # TODO: validate image exists - upload if not?
        self._post('images/display', dict(FileName=file_name, TimeOutSeconds=time_out_secs, Alpha=alpha))

    def set_led(self, rgb: RGB):
        rgb.validate()
        self._post('led', rgb.json)

    def delete(self, file_name: str):
        self._delete('images', dict(FileName=file_name))

    @staticmethod
    def _validate_take_picture(file_name, width, height, show_on_screen):
        if bool(width) + bool(height) == 1:
            raise ValueError("must supply both width and height, or neither. can't supply just one")

        if show_on_screen and not file_name:
            raise ValueError('in order for `show_on_screen` to work, you must provide a file_name')

    def take_picture(self, file_name: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None,
                     *, get_result: bool = True, show_on_screen: Optional[bool] = False,
                     overwrite_existing=True):
        self._validate_take_picture(file_name, width, height, show_on_screen)

        payload = json_obj()
        payload.add_if_not_none(Base64=get_result, FileName=file_name, Width=width, Height=height,
                                DisplayOnScreen=show_on_screen, OverwriteExisting=overwrite_existing)
        return self._get_j('cameras/rgb', **payload)

    def start_recording_video(self):
        """
        video is limited:
        - records up to 10 seconds
        - can only store one recording at a time
        """
        self._post('video/record/start')

    def stop_recording_video(self):
        self._post('video/record/stop')

    def get_recorded_video(self):
        return self._get_j('video')


class AudioAPI(SubAPI):
    def __init__(self, api: MistyAPI):
        super().__init__(api)
        self.audio = self.list()

    def get(self, file_name: str) -> Any:
        # TODO: what the hell do we get back?
        return self._get_j('audio', FileName=file_name)

    def list(self) -> Dict[str, Audio]:
        audio = (Audio.from_misty(a) for a in self._get_j('audio/list'))
        return {a.name: a for a in audio}

    def upload(self, file_name: str, as_byte_array: bool = False, apply_immediately: bool = False,
               overwrite: bool = True):
        if as_byte_array:
            raise ValueError('uploading `as_byte_array` is not currently supported')

        payload = dict(FileName=file_name, ImmediatelyApply=apply_immediately, OverwriteExisting=overwrite)
        self._post('audio', payload)

    def play(self, file_name_or_id: str, volume: int = 100, as_file_name: bool = True):
        volume = min(max(volume, 1), 100)
        payload = dict(Volume=volume)
        payload['FileName' if as_file_name else 'AssetId'] = file_name_or_id
        self._post('audio/play', payload)

    def delete(self, file_name: str):
        self._delete('audio', dict(FileName=file_name))

    def set_default_volume(self, volume):
        self._post('audio/volume', dict(Volume=min(max(volume, 0), 100)))


class FaceAPI(SubAPI):
    def __init__(self, api: MistyAPI):
        super().__init__(api)
        self.faces = self.list()

    def cancel_training(self):
        """shouldn't need to call unless you want to manually stop something in progress"""
        self._get('faces/training/cancel')

    def list(self) -> List[str]:
        return self._get_j('faces')

    def delete(self, *, name: Optional[str] = None, delete_all: bool = False):
        """rm faces from misty"""
        if (delete_all and name) or not (delete_all or name):
            raise ValueError('set exactly one of `name` or `delete_all`')

        kwargs = {}
        if name:
            kwargs['FaceId'] = name

        self._delete('faces', **kwargs)

    def start_detection(self):
        """
        start finding/detecting faces in misty's line of vision

        TODO: subscribe to FaceEvents to figure when done
        """
        self._post('faces/detection/start')

    def stop_detection(self):
        """stop finding/detecting faces in misty's line of vision"""
        self._post('faces/detection/stop')

    def start_training(self):
        """
        start training a particular face

        TODO: subscribe to FaceEvents to figure when done
        TODO: set up something to alert the user that this is happening
            - change LED colors, display some text
        """
        self._post('faces/training/start')

    def stop_training(self):
        """stop training a particular face"""
        self._post('faces/training/stop')

    def start_recognition(self):
        self._post('faces/recognition/start')

    def stop_recognition(self):
        """stop attempting to recognize faces"""
        self._post('faces/recognition/stop')


class MovementAPI(SubAPI):
    @staticmethod
    def _validate_vel_pct(**vel_pcts):
        fails = {}
        for name, val in vel_pcts.items():
            if not -100 <= val <= 100:
                fails[name] = val
        if fails:
            raise ValueError(f'invalid value for vel_pct: {fails}, must be in range [-100, 100]')

    def drive(self, linear_vel_pct: int, angular_vel_pct: int):
        return self.drive_time(linear_vel_pct, angular_vel_pct)

    def drive_time(self, linear_vel_pct: int, angular_vel_pct: int, time_ms: Optional[int] = None):
        """
        angular_vel_pct: -100 is full speed clockwise, 100 is full speed counter-clockwise
        """
        self._validate_vel_pct(linear_vel_pct=linear_vel_pct, angular_vel_pct=angular_vel_pct)
        payload = dict(LinearVelocity=linear_vel_pct, AngularVelocity=angular_vel_pct)
        endpoint = 'drive'
        if time_ms:
            payload['TimeMS'] = time_ms
            endpoint += '/time'

        self._post(endpoint, payload)

    def drive_track(self, left_track_vel_pct: float = 0.0, right_track_vel_pct: float = 0.0):
        """control drive tracks individually"""
        self._validate_vel_pct(left_track_vel_pct=left_track_vel_pct, right_track_vel_pct=right_track_vel_pct)
        self._post('drive/track', dict(LeftTrackSpeed=left_track_vel_pct, RightTrackSpeed=right_track_vel_pct))

    def move_arms(self, *arm_settings: ArmSettings):
        """pass either/both left and right arm settings"""
        self._post('arms/set', {k: v for arm in arm_settings for k, v in arm.json.items()})

    def move_head(self, settings: HeadSettings):
        self._post('head', settings.to_misty())

    def stop(self, *, everything=False):
        """
        stop motion

        if `everything` is set, will stop everything (i.e. halt)
        """
        if everything:
            return self.halt()
        self._post('drive/stop')

    def halt(self):
        """stop everything"""
        self._post('robot/halt')


class SystemAPI(SubAPI):
    def clear_error_msg(self):
        self._post('text/clear')

    @property
    def networks(self) -> List[Wifi]:
        return [Wifi.from_misty(o) for o in self._get_j('networks')]

    @property
    def battery(self):
        return self._get_j('battery')

    @property
    def device_info(self):
        return self._get_j('device')

    def help(self, command: Optional[str] = None):
        params = json_obj(command=command)
        return self._get_j('help', **params)

    def get_logs(self):
        # TODO: implement individual date functionality
        return self._get_j('logs')

    def perform_system_update(self):
        self._post('system/update')

    def set_wifi_network(self, name, password):
        payload = dict(NetworkName=name, Password=password)
        self._post('network', payload)

    def trigger_skill_event(self, skill_uid: str, event_name: str, json: Optional[Dict]):
        """send an event to a currently running skill"""
        payload = json_obj(UniqueId=skill_uid, EventName=event_name, Payload=json)
        self._post('skills/event', payload)

    def send_to_backpack(self, msg: str):
        """not sure what kind of data/msg we can send - perhaps Base64 encode to send binary data?"""
        self._post('serial', dict(Message=msg))


class _SlamHelper(SubAPI):
    def __init__(self, api: MistyAPI, endpoint: str):
        super().__init__(api)
        self._endpoint = endpoint
        self.num_current_slam_streams = 0

    def start(self):
        return self._post(f'slam/{self._endpoint}/start')

    def stop(self):
        return self._post(f'slam/{self._endpoint}/stop')

    def __enter__(self):
        if self.num_current_slam_streams == 0:
            self.start()
        self.num_current_slam_streams += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.num_current_slam_streams -= 1
        if self.num_current_slam_streams == 0:
            self.stop()


class NavigationAPI(SubAPI):
    def __init__(self, api: MistyAPI):
        super().__init__(api)
        self.slam_streaming = _SlamHelper(api, 'streaming')
        self.slam_mapping = _SlamHelper(api, 'map')
        self.slam_tracking = _SlamHelper(api, 'track')

    def reset_slam(self):
        return self._post('slam/reset')

    def take_depth_pic(self):
        with self.slam_streaming:
            return self._get_j('cameras/depth')

    def take_fisheye_pic(self):
        with self.slam_streaming:
            return self._get_j('cameras/fisheye')

    def get_map(self):
        with self.slam_mapping:
            return self._get_j('slam/map')

    @staticmethod
    def _format_coords(*coords: Coords):
        return ','.join(f'{c.x}:{c.y}' for c in coords)

    def drive_to_coordinates(self, coords: Coords):
        with self.slam_tracking:
            self._post('drive/coordinates', dict(Destination=self._format_coords(coords)))

    def follow_path(self, *coords: Coords):
        with self.slam_tracking:
            if len(coords) == 1:
                return self.drive_to_coordinates(*coords)
            return self._post('drive/path', dict(Path=self._format_coords(*coords)))


class SkillAPI(SubAPI):
    def stop(self, skill_name: Optional[str] = None):
        self._post('skills/cancel', json_obj(Skill=skill_name))

    def delete(self, skill_uid: str):
        self._delete(Skill=skill_uid)

    def get_running(self):
        return [Skill.from_misty(s) for s in self._get_j('skills/running')]

    def get(self):
        return self._get_j('skills')

    def run(self, skill_name_or_uid, method: Optional[str] = None):
        return self._post('skills/start', json_obj(Skill=skill_name_or_uid, Method=method)).json()['result']

    def save(self, zip_file_name: str, apply_immediately: bool = False, overwrite_existing: bool = True):
        self._post('skills', dict(File=zip_file_name, ImmediatelyApply=apply_immediately,
                                  OverwriteExisting=overwrite_existing))


# ======================================================================================================================

class MistyAPI(RestAPI):
    def __init__(self, ip):
        self.ip = ip

        self.backpack_instance = None
        self.time_of_flight_instance = [None] * 4
        self.face_recognition_instance = None

        self.available_subscriptions = ["StringMessage", "TimeOfFlight", "FaceDetection", "FaceRecognition",
                                        "LocomotionCommand", "HaltCommand", "SelfState", "WorldState"]

    # ==================================================================================================================
    # Sub APIs
    # ==================================================================================================================

    images: ImageAPI = APIDescriptor()
    audio: AudioAPI = APIDescriptor()
    faces: FaceAPI = APIDescriptor()
    movement: MovementAPI = APIDescriptor()
    system: SystemAPI = APIDescriptor()
    navigation: NavigationAPI = APIDescriptor()
    skills: SkillAPI = APIDescriptor()

    # ==================================================================================================================
    # ==================================================================================================================
    # REST CALLS
    # ==================================================================================================================
    def _endpoint(self, endpoint, **params) -> str:
        res = f'http://{self.ip}/api/{endpoint}'

        if params:
            param_str = '&'.join(f'{k}={v}' for k, v in params.items())
            res = f'{res}?{param_str}'

        return res

    def _get(self, endpoint, **params):
        return requests.get(self._endpoint(endpoint, **params))

    def _get_j(self, endpoint, **params):
        return self._get(endpoint, **params).json()['result']

    def _post(self, endpoint, json: Optional[dict] = None, **params):
        return requests.post(self._endpoint(endpoint, **params), json=json)

    def _delete(self, endpoint, json: Optional[dict] = None, **params):
        return requests.delete(self._endpoint(endpoint, **params), json=json)
