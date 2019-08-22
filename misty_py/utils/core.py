import asyncio
import json
from abc import abstractmethod, ABC
from asyncio import Future
from contextlib import suppress
from functools import wraps
from pathlib import Path
from typing import NamedTuple, Dict, Optional, Union, List, Set, Any, Coroutine
from collections import ChainMap, defaultdict
from PIL import Image as PImage
from base64 import b64decode, b64encode
from io import BytesIO

__all__ = (
    'Coords', 'InstanceCache', 'json_obj', 'RestAPI', 'JSONObjOrObjs', 'decode_img',
    'save_data_locally', 'generate_upload_payload', 'delay', 'asyncpartial', 'classproperty', 'wait_first',
    'async_run', 'format_help', 'wait_in_order', 'wait_for_group', 'first'
)


def first(v):
    return next(iter(v))


class classproperty:
    def __init__(self, f):
        self.f = f

    def __get__(self, instance, cls):
        return self.f(cls)


def asyncpartial(coro, *args, **kwargs):
    @wraps(coro)
    async def wrapped(*a, **kw):
        return await coro(*args, *a, **kwargs, **kw)

    return wrapped


class Coords(NamedTuple):
    x: int
    y: int

    def __str__(self):
        return f'{self.x}:{self.y}'

    @staticmethod
    def format(*coords: 'Coords'):
        return ','.join(map(str, coords))


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
    """
    singleton-ish metaclass

    create one instance per args used to instantiate class:
    >>> class A(metaclass=InstanceCache)
    >>>     def __init__(self, jeb):
    >>>         pass
    >>> a1 = A('abcd')
    >>> a2 = A('abcd')
    >>> a3 = A('6')
    >>> a1 is a2  # True
    >>> a1 is a3  # False
    """

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


def encode_data(filename_or_bytes: Union[str, bytes], limit: int = None) -> str:
    """transform either a filename or bytes to base64 encoding"""
    data = filename_or_bytes
    if isinstance(filename_or_bytes, str):
        with open(filename_or_bytes, 'rb') as f:
            data = f.read()
    return b64encode(data[:limit]).decode()


def decode_data(data: Union[str, bytes, BytesIO]) -> BytesIO:
    """decode base64 data"""
    if isinstance(data, BytesIO):
        return data
    res = data
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


def generate_upload_payload(prefix, file_name, apply_immediately, overwrite_existing, limit=None):
    """
    upload for audio/images are very similar. this function encapsulates that

    `limit` can be used with audio - to limit the file size to the current (paltry) 3mb
    """
    # TODO: add back in when misty supports path prefixes
    # return json_obj(FileName=str(Path(prefix) / Path(file_name).name), Data=encode_data(file_name, limit),
    #                 ImmediatelyApply=apply_immediately, OverwriteExisting=overwrite_existing)
    return json_obj(FileName=Path(file_name).name, Data=encode_data(file_name, limit),
                    ImmediatelyApply=apply_immediately, OverwriteExisting=overwrite_existing)


async def delay(how_long_secs, to_run: Coroutine):
    """
    run `to_run` coroutine after `how_long_secs`
    if provided, `cb` (callback) will be called when done
    """
    if how_long_secs is None or how_long_secs <= 0:
        return await to_run
    return await wait_in_order(asyncio.sleep(how_long_secs), to_run)


async def wait_in_order(*coros: Optional[Union[Future, Coroutine]]):
    """await coros in order. return results"""
    try:
        return [(await c) if c else None for c in coros]
    except asyncio.CancelledError:
        for c in coros:
            if c:
                c.close()
        raise


async def wait_for_group(*coros):
    """
    await all coros simultaneously via gather
    useful when chaining a bunch of commands together via `wait_in_order`
    """
    return await asyncio.gather(*coros)


class DonePending(NamedTuple):
    """futures that have completed and futures that are still pending"""
    done: Set[asyncio.Future]
    pending: Set[asyncio.Future]


async def wait_first(*coros: Optional[Coroutine], cancel=True, return_when=asyncio.FIRST_COMPLETED) -> DonePending:
    """
    wait for the first task to complete (default) or raise an exception.

    by default, cancel all pending futures
    """
    coros = [c for c in coros if c]
    if not coros:
        return DonePending(set(), set())

    done, pending = await asyncio.wait(coros, return_when=return_when)
    g = asyncio.gather(*pending)
    if cancel:
        g.cancel()
    with suppress(asyncio.CancelledError):
        await g
    return DonePending(done, pending)


def format_help(help):
    """
    make misty's help information more accessible
        - group methods via their `apiCommandGroup`
        - print the values nicely

    return the dict
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


async def _await_all():
    """await any remaining tasks"""
    for t in asyncio.all_tasks():
        with suppress(Exception):
            await t


async def _async_run_helper(coro):
    await coro
    await _await_all()


def async_run(coro):
    """
    run coro and then drain any pending tasks
    a seemingly better substitute for `asyncio.run`
    """
    asyncio.run(_async_run_helper(coro))

# class aobject:
#     """enable async init of objects"""
#     async def __new__(cls, *args, **kwargs):
#         instance = super().__new__(cls)
#         await instance.__init__(*args, **kwargs)
#         return instance
#
#     async def __init__(self):
#         pass
