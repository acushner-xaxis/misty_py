import asyncio
import json
from abc import abstractmethod, ABC
from enum import IntFlag, Enum
from functools import wraps
from pathlib import Path
from typing import NamedTuple, Dict, Optional, Union, List, Set, Any, Coroutine
from collections import ChainMap, defaultdict
from PIL import Image as PImage
from base64 import b64decode, b64encode
from io import BytesIO

__all__ = (
    'SlamStatus', 'Coords', 'InstanceCache', 'ArmSettings', 'HeadSettings', 'json_obj', 'RestAPI', 'JSONObjOrObjs',
    'decode_img', 'save_data_locally', 'generate_upload_payload', 'delay', 'MISTY_URL', 'asyncpartial', 'classproperty'
)

MISTY_URL = 'http://192.168.86.249'


class classproperty:
    def __init__(self, f):
        self.f = f

    def __get__(self, instance, cls):
        return self.f(cls)


def asyncpartial(coro, *args, **kwargs):
    @wraps(coro)
    async def wrapped(*a, **kw):
        await coro(*(args + a), **{**kwargs, **kw})

    return wrapped


class SlamStatus(IntFlag):
    streaming = 1
    exploring = 2
    tracking = 4
    recording = 8
    resetting = 16
    paused = 32

    @property
    def title(self):
        return self.name.title()


class Coords(NamedTuple):
    x: int
    y: int

    def __str__(self):
        return f'{self.x}:{self.y}'

    @staticmethod
    def format(*coords: 'Coords'):
        return ','.join(map(str, coords))


def _denormalize(obj) -> Dict[str, float]:
    """
    transform values generally in the range [-100.0, 100] to values misty is expecting

    this function is not in a base class due to NamedTuple's custom mro setup
    """
    attrs = ((k, v) for k, v in obj._var_range.items() if getattr(obj, k) is not None)
    return dict((k, getattr(obj, k) / 100 * v) for k, v in attrs)


class ArmSettings(NamedTuple):
    """
    all vals in range [-100.0, 100.0]
    will automatically denormalize to values accepted by misty

    -100 = down, 100 = up
    """
    side: str  # left | right
    position: float
    velocity: float = 100

    _var_range = dict(position=-90, velocity=10)

    @property
    def json(self) -> Dict[str, float]:
        side = self.side.lower()
        return {f'{side}Arm{k.capitalize()}': v for k, v in _denormalize(self).items()}


class HeadSettings(NamedTuple):
    """
    all vals in range [-100.0, 100.0]
    will automatically denormalize to values accepted by misty

    pitch: up and down
    roll: tilt (ear to shoulder)
    yaw: turn left and right
    velocity: how quickly
    """
    pitch: Optional[float] = None
    roll: Optional[float] = None
    yaw: Optional[float] = None
    velocity: Optional[float] = None

    _var_range = dict(pitch=-10, roll=50, yaw=-100, velocity=100)

    @property
    def json(self) -> Dict[str, float]:
        return {k.capitalize(): v for k, v in _denormalize(self).items() if v is not None}


# ======================================================================================================================

identity = lambda x: x


class json_obj(dict):
    """add `.` accessibility to dicts"""

    def __new__(cls, dict_or_list: Optional[Union[dict, list]] = None, **kwargs):
        if isinstance(dict_or_list, list):
            if kwargs:
                raise ValueError('cannot pass list with keyword args')
            return [(json_obj if isinstance(e, (dict, list)) else identity)(e) for e in dict_or_list]

        new_dict = kwargs
        if isinstance(dict_or_list, dict):
            new_dict = ChainMap(kwargs, dict_or_list)
        elif dict_or_list is not None:
            # try to process as an iterable of tuples, a la regular dict creation
            new_dict = ChainMap(kwargs, {k: v for (k, v) in dict_or_list})

        res = super().__new__(cls)
        res._add(**new_dict)
        return res

    def __init__(self, _=None, **__):
        """need to suppress dict's default init, otherwise subdictionaries won't appear as json_obj types"""

    @classmethod
    def from_not_none(cls, **key_value_pairs):
        """create new obj and add only items that aren't `None`"""
        res = cls()
        res.add_if_not_none(**key_value_pairs)
        return res

    @classmethod
    def from_str(cls, s: str):
        return cls(json.loads(s))

    @property
    def json_str(self) -> str:
        return json.dumps(self)

    @property
    def pretty(self) -> str:
        return json.dumps(self, indent=4, sort_keys=True)

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
        return value

    def __getattr__(self, key):
        return self[key]

    def __delattr__(self, key):
        del self[key]

    def __and__(self, other) -> Set[Any]:
        return self.keys() & other.keys()

    def __or__(self, other) -> Set[Any]:
        return self.keys() | other.keys()

    def __xor__(self, other) -> 'json_obj':
        cm = ChainMap(self, other)
        return type(self)((k, cm[k]) for k in self.keys() ^ other.keys())

    def __str__(self):
        strs = (f'{k}={v!r}' for k, v in self.items())
        return f'json_obj({", ".join(strs)})'

    __repr__ = __str__


JSONObjOrObjs = Union[json_obj, List[json_obj]]


class RestAPI(ABC):
    @abstractmethod
    def _get(self, endpoint, *, _headers=None, **params):
        """REST GET"""

    @abstractmethod
    def _get_j(self, endpoint, *, _headers=None, **params) -> JSONObjOrObjs:
        """REST GET - return as dict"""

    @abstractmethod
    def _post(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        """REST POST"""

    @abstractmethod
    def _delete(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        """REST DELETE"""


class InstanceCache(type):
    """create only one instance per args passed to class"""

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


def encode_data(filename_or_bytes: Union[str, bytes]) -> str:
    """transform either a filename or bytes to base64 encoding"""
    data = filename_or_bytes
    if isinstance(filename_or_bytes, str):
        with open(filename_or_bytes, 'rb') as f:
            data = f.read()
    return b64encode(data).decode()


def decode_data(data_base64) -> BytesIO:
    """decode base64 data"""
    if isinstance(data_base64, BytesIO):
        return data_base64
    res = data_base64
    if isinstance(res, str):
        res = res.encode()
    if b',' in res:
        res = res[res.index(b',') + 1:]
    return BytesIO(b64decode(res))


def decode_img(img_b64, display_image=True) -> BytesIO:
    res = decode_data(img_b64)
    if display_image:
        PImage.open(res)
    return res


def save_data_locally(path, data: BytesIO, suffix: str):
    """given a filename, data, and suffix, write out data"""
    with open(Path(path).with_suffix(suffix), 'wb') as f:
        f.write(data.read())


def generate_upload_payload(file_name, apply_immediately, overwrite_existing):
    """upload for audio/images are very similar. this function encapsulates that"""
    return json_obj(FileName=Path(file_name).name, Data=encode_data(file_name),
                    ImmediatelyApply=apply_immediately, OverwriteExisting=overwrite_existing)


async def delay(how_long_secs, to_run: Coroutine, cb: Optional[Coroutine] = None):
    """
    run `to_run` coroutine after `how_long_secs`
    if provided, `cb` (callback) will be called when done
    """
    await asyncio.sleep(how_long_secs)
    await to_run
    if cb:
        await cb


def format_help(help):
    """
    parse json from misty's help in a useful way
    print the values nicely
    """
    res = defaultdict(list)
    for method, commands in help.items():
        method = method.upper()
        for cmd in commands:
            res[cmd.apiCommand.apiCommandGroup].append((method, cmd))

    def pp(l):
        for method, d in l:
            print(f'{d.baseApiCommand}: {method} {d.endpoint}')

    for k, v in res.items():
        print(f'============{k}=============')
        pp(v)
        print()
    return res

# class aobject:
#     """enable async init of objects"""
#     async def __new__(cls, *args, **kwargs):
#         instance = super().__new__(cls)
#         await instance.__init__(*args, **kwargs)
#         return instance
#
#     async def __init__(self):
#         pass
