import asyncio
import json
from abc import abstractmethod, ABC
from enum import IntFlag
from typing import NamedTuple, Dict, Optional

__all__ = ('SlamStatus', 'Coords', 'Wifi', 'Skill', 'Image', 'Audio',
           'ArmSettings', 'HeadSettings', 'json_obj', 'RestAPI')


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
        return cls(d['Name'], d['Width'], d['Height'], d.get('userAddedAsset'))


class Audio(NamedTuple):
    name: str
    user_added: bool

    @classmethod
    def from_misty(cls, d):
        return cls(d['Name'], d.get('userAddedAsset'))


class ArmSettings(NamedTuple):
    side: str  # left | right
    position: float  # [-5, 5]
    velocity: float = 100  # [0, 100]

    def validate(self):
        errors = []
        if self.side.lower() not in ('left', 'right'):
            errors.append(f'invalid side {self.side!r}, must be either "left" or "right"')
        if not -5 <= self.position <= 5:
            errors.append(f'invalid position {self.position}, must be in [-5, 5]')
        if not 0 <= self.velocity <= 100:
            errors.append(f'invalid velocity {self.velocity}, must be in [0, 100]')

        if errors:
            raise ValueError('\n'.join(errors))

    @property
    def json(self) -> Dict[str, float]:
        self.validate()
        side = self.side.lower()
        return {f'{side}ArmPosition': self.position + 5, f'{side}ArmVelocity': self.velocity}


class HeadSettings(NamedTuple):
    pitch: Optional[float] = None  # up and down [-5, 5]
    roll: Optional[float] = None  # tilt (ear to shoulder) [-5, 5]
    yaw: Optional[float] = None  # turn left and right [-5, 5]
    velocity: Optional[float] = None  # [0, 10]

    @property
    def json(self) -> Dict[str, float]:
        return {k.capitalize(): v for k, v in self._asdict().items() if v is not None}


# ======================================================================================================================

class json_obj(dict):
    def __init__(self, **kwargs):
        super().__init__()
        self._add(**kwargs)

    @classmethod
    def from_not_none(cls, **key_value_pairs):
        res = cls()
        res.add_if_not_none(**key_value_pairs)

    def _add(self, _if_not_none=False, **key_value_pairs):
        for k, v in key_value_pairs.items():
            if not _if_not_none or v is not None:
                if isinstance(v, dict):
                    self[k] = json_obj(**v)
                else:
                    self[k] = v

    def add_if_not_none(self, **key_value_pairs):
        self._add(_if_not_none=True, **key_value_pairs)

    def __setattr__(self, key, value):
        d = {key: value}
        self._add(**d)

    def __getattr__(self, key):
        return self[key]

    def __delattr__(self, key):
        del self[key]

    @property
    def json_str(self) -> str:
        return json.dumps(self)

    @classmethod
    def from_str(cls, s: str):
        return cls(**json.loads(s))

    def __str__(self):
        strs = (f'{k}={v!r}' for k, v in self.items())
        return f'json_obj({", ".join(strs)})'

    __repr__ = __str__


class RestAPI(ABC):
    @abstractmethod
    def _get(self, endpoint, **params):
        """REST GET"""

    @abstractmethod
    def _get_j(self, endpoint, **params) -> Dict:
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
