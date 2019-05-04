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
    """will only add values if they are not `None`"""

    def __init__(self, **kwargs):
        super().__init__()
        self.add_if_not_none(**kwargs)

    def add_if_not_none(self, **key_value_pairs):
        for k, v in key_value_pairs.items():
            if v is not None:
                self[k] = v

    def __setattr__(self, key, value):
        self[key] = value

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
