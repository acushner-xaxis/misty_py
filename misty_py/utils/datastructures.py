import asyncio
import json
from abc import abstractmethod, ABC
from enum import IntFlag
from typing import NamedTuple, Dict, Optional, Any, Union, List
from collections import ChainMap
from PIL import Image as PImage
from base64 import b64decode
from io import BytesIO

__all__ = ('SlamStatus', 'Coords', 'Wifi', 'Skill', 'Image', 'Audio', 'Singleton', 'ArmSettings', 'HeadSettings',
           'json_obj', 'RestAPI', 'JSONObjOrObjs', 'decode_img')


class SlamStatus(IntFlag):
    idle = 1
    exploring = 2
    tracking = 4
    recording = 8
    resetting = 16


# ======================================================================================================================

class Coords(NamedTuple):
    x: int
    y: int


class Wifi(NamedTuple):
    name: str
    signal_strength: int
    is_secure: bool

    @classmethod
    def from_misty(cls, d: Dict):
        return cls(d['Name'], d['SignalStrength'], d['IsSecure'])


class Skill(NamedTuple):
    name: str
    description: str
    startup_args: Dict
    uid: str

    @classmethod
    def from_misty(cls, d):
        return cls(d['name'], d['description'], d['startupArguments'], d['uniqueId'])


class Image(NamedTuple):
    name: str
    width: int
    height: int
    user_added: Optional[bool]

    @classmethod
    def from_misty(cls, d):
        return cls(d['name'], d['width'], d['height'], d.get('systemAsset'))


class Audio(NamedTuple):
    name: str
    user_added: bool

    @classmethod
    def from_misty(cls, d):
        return cls(d['Name'], d.get('userAddedAsset'))


def _denormalize(obj) -> Dict[str, float]:
    attrs = ((k, v) for k, v in obj._var_range.items() if getattr(obj, k) is not None)
    return dict((k, getattr(obj, k) / 100 * v) for k, v in attrs)


class ArmSettings(NamedTuple):
    side: str  # left | right
    position: float  # [-5, 5]
    velocity: float = 100  # [0, 100]

    _var_range = dict(position=-100, velocity=100)

    @property
    def json(self) -> Dict[str, float]:
        side = self.side.lower()
        return {f'{side}Arm{k.capitalize()}': v for k, v in _denormalize(self).items()}


class HeadSettings(NamedTuple):
    """
    all vals in range [-100, 100]

    pitch: up and down
    roll: tilt (ear to shoulder)
    yaw: turn left and right
    velocity: how quickly
    """
    pitch: Optional[float] = None
    roll: Optional[float] = None
    yaw: Optional[float] = None
    velocity: Optional[float] = None

    _var_range = dict(pitch=-10, roll=50, yaw=-100, velocity=10)

    @property
    def json(self) -> Dict[str, float]:
        return {k.capitalize(): v for k, v in _denormalize(self).items() if v is not None}


# ======================================================================================================================

identity = lambda x: x


class json_obj(dict):
    def __new__(cls, dict_or_list: Optional[Union[dict, list]] = None, **kwargs):
        if isinstance(dict_or_list, list):
            if kwargs:
                raise ValueError('cannot pass list with keyword args')
            return [(json_obj if isinstance(e, (dict, list)) else identity)(e) for e in dict_or_list]

        new_dict = kwargs
        if isinstance(dict_or_list, dict):
            new_dict = ChainMap(kwargs, dict_or_list)
        elif dict_or_list is not None:
            # try process as an iterable of tuples, a la regular dict creation
            new_dict = {k: v for (k, v) in dict_or_list}

        res = super().__new__(cls)
        res._add(**new_dict)
        return res

    def __init__(self, _=None, **__):
        """need to supress dict's default init, otherwise subdictionaries won't appear as json_obj types"""

    @classmethod
    def from_not_none(cls, **key_value_pairs):
        res = cls()
        res.add_if_not_none(**key_value_pairs)
        return res

    @property
    def json_str(self) -> str:
        return json.dumps(self)

    @classmethod
    def from_str(cls, s: str):
        return cls(**json.loads(s))

    def add_if_not_none(self, **key_value_pairs):
        self._add(_if_not_none=True, **key_value_pairs)

    def _add(self, _if_not_none=False, **key_value_pairs):
        for k, v in key_value_pairs.items():
            if not _if_not_none or v is not None:
                if isinstance(v, (list, dict)):
                    self[k] = json_obj(v)
                else:
                    self[k] = v

    def __setattr__(self, key, value):
        self._add(**{key: value})

    def __getattr__(self, key):
        return self[key]

    def __delattr__(self, key):
        del self[key]

    def __str__(self):
        strs = (f'{k}={v!r}' for k, v in self.items())
        return f'json_obj({", ".join(strs)})'

    __repr__ = __str__


JSONObjOrObjs = Union[json_obj, List[json_obj]]


class RestAPI(ABC):
    @abstractmethod
    def _get(self, endpoint, **params):
        """REST GET"""

    @abstractmethod
    def _get_j(self, endpoint, **params) -> JSONObjOrObjs:
        """REST GET - return as dict"""

    @abstractmethod
    def _post(self, endpoint, json: Optional[dict] = None, **params):
        """REST POST"""

    @abstractmethod
    def _delete(self, endpoint, json: Optional[dict] = None, **params):
        """REST DELETE"""


# class aobject:
#     """enable async init of objects"""
#     async def __new__(cls, *args, **kwargs):
#         instance = super().__new__(cls)
#         await instance.__init__(*args, **kwargs)
#         return instance
#
#     async def __init__(self):
#         pass


class Singleton(type):
    def __new__(mcs, name, bases, body):
        cls = super().__new__(mcs, name, bases, body)
        cls._cache = {}
        return cls

    def __call__(cls, *args):
        try:
            res = cls._cache[args]
        except KeyError:
            res = cls._cache[args] = super().__call__(*args)
        return res


def decode_img(img_b64, display_image=True):
    res = b64decode(img_b64[img_b64.index(',') + 1:])
    if display_image:
        PImage.open(BytesIO(res))
    return res
