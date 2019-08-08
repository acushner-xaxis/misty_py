from __future__ import annotations

import asyncio
from abc import abstractmethod
from contextlib import suppress
from enum import Enum
from itertools import count
from typing import NamedTuple, Set, Optional, Callable, Awaitable, FrozenSet, Generator, Dict, List, Any

import arrow

from misty_py.utils import json_obj
from misty_py.utils.core import classproperty

__author__ = 'acushner'

HandlerType = Callable[['SubPayload'], Awaitable[Any]]


class SubType(Enum):
    """
    high-level subscription types

    enum of broader subscriptions misty will accept
    these can be further refined with `EventCondition`s
    """
    actuator_position = 'ActuatorPosition'
    audio_play_complete = 'AudioPlayComplete'
    battery_charge = 'BatteryCharge'
    bump_sensor = 'BumpSensor'
    drive_encoders = 'DriveEncoders'
    face_recognition = 'FaceRecognition'
    halt_command = 'HaltCommand'
    imu = 'IMU'
    key_phrase_recognized = 'KeyPhraseRecognized'
    locomotion_command = 'LocomotionCommand'
    self_state = 'SelfState'
    serial_message = 'SerialMessage'
    time_of_flight = 'TimeOfFlight'
    touch_sensor = 'TouchSensor'
    world_state = 'WorldState'

    @property
    def lower_level_subs(self):
        """yield either a single value or specific values depending on SubType"""
        t = _high_to_low_level_sub_map.get(self)
        if not t:
            yield Sub.create(self)
        else:
            yield from (s.sub for s in t)


class EventCondition(NamedTuple):
    """when used with `SubType`s can further clarify/focus a subscription"""
    name: str
    value: str
    inequality: str = '='

    _valid_inequalities = frozenset('= != > < >= <= empty exists'.split())

    @property
    def json(self) -> json_obj:
        return json_obj(Property=self.name, Inequality=self.inequality, Value=self.value)

    def __str__(self):
        return f'{self.name}{self.inequality}{self.value}'


_high_to_low_level_sub_map: Dict[SubType, 'LLSubType'] = {}


class LLSubType(Enum):
    """
    lower level `SubType`s.
    represent more granular subscriptions on misty

    some `SubType`s, like `actuator_position`, require that you add certain `EventCondition`s
    in order to access the data, and classes that inherit from this represent these lower-level subscriptions
    """

    def __init_subclass__(cls, **kwargs):
        _high_to_low_level_sub_map[cls._sub_type] = cls

    @abstractmethod
    @classproperty
    def _sub_type(cls) -> SubType:
        """fill in with the associated subscription type"""

    @property
    def _event_condition(self) -> EventCondition:
        return EventCondition('sensorId', self.value)

    @property
    def sub(self) -> Sub:
        return Sub.create(self._sub_type, self._event_condition)


class Touch(LLSubType):
    # TODO: get abbreviated values for `Touch` from misty?
    """in the `sensorPosition` var"""

    chin = 'Chin'
    chin_left = 'ChinLeft'
    chin_right = 'ChinRight'
    head_left = 'HeadLeft'
    head_right = 'HeadRight'
    head_back = 'HeadBack'
    head_front = 'HeadFront'
    head_top = 'HeadTop'
    scruff = 'Scruff'

    @property
    def _event_condition(self) -> EventCondition:
        return EventCondition('sensorPosition', self.value)

    @classproperty
    def _sub_type(cls) -> SubType:
        return SubType.touch_sensor


class Bump(LLSubType):
    """sensor that indicates whether you hit something"""

    front_right = 'bfr'
    front_left = 'bfl'
    back_right = 'bbr'
    back_left = 'bbl'

    @classproperty
    def _sub_type(cls) -> SubType:
        return SubType.bump_sensor


class Actuator(LLSubType):
    """sensor that monitors the various positions of the head and arms"""
    pitch = 'ahp'
    yaw = 'ahy'
    roll = 'ahr'
    left_arm = 'ala'
    right_arm = 'ara'

    @classproperty
    def _sub_type(cls) -> SubType:
        return SubType.actuator_position


# class TimeOfFlight(LLSubType):
#     @classproperty
#     def _sub_type(cls) -> SubType:
#         return SubType.time_of_flight


class IMU(LLSubType):
    """inertial measurement unit"""
    yaw = 'Yaw'
    pitch = 'Pitch'
    roll = 'Roll'
    x_acceleration = 'XAcceleration'
    y_acceleration = 'YAcceleration'
    z_acceleration = 'ZAcceleration'
    pitch_velocity = 'PitchVelocity'
    roll_velocity = 'RollVelocity'
    yaw_velocity = 'YawVelocity'

    @classproperty
    def _sub_type(cls) -> SubType:
        return SubType.imu


class DriveEncoder(LLSubType):
    left_distance = 'LeftDistance'
    right_distance = 'RightDistance'
    left_velocity = 'LeftVelocity'
    right_velocity = 'RightVelocity'

    @classproperty
    def _sub_type(cls) -> SubType:
        return SubType.drive_encoders


# ======================================================================================================================


class Sub(NamedTuple):
    """
    subscription object representing all the data necessary to make a subscription to misty's websockets

    this includes:
    - the higher level `SubType`
    - any `EventCondition`s you might need (including ones represented by `LLSubType` enums)
    - a return property, which pares down the amount of data you get back
    """
    sub: SubType
    ec: FrozenSet[EventCondition] = frozenset()
    return_prop: Optional[str] = None

    @classmethod
    def create(cls, sub: SubType, *ec: EventCondition, return_prop: str = None):
        return cls(sub, frozenset(ec), return_prop)

    def __str__(self):
        res = [self.sub.value]
        if self.ec:
            res.append('|'.join(map(str, self.ec)))
        if self.return_prop:
            res.append(f'return={self.return_prop}')
        return ':'.join(res)


class SubId(NamedTuple):
    """subscription identifier"""
    id: int
    type: Sub
    api: 'MistyAPI'

    _count = count(1)

    @classmethod
    def create(cls, sub, api):
        return cls(next(cls._count), sub, api)

    @property
    def event_name(self) -> str:
        return f'{str(self.type)}-{self.id:04}'

    async def unsubscribe(self):
        return await self.api.ws.unsubscribe(self)


class SubPayload(NamedTuple):
    """payload from a subscription with additional metadata"""
    time: arrow.Arrow
    data: json_obj
    sub_id: SubId

    @classmethod
    def from_data(cls, o: json_obj, sid: SubId):
        return cls(arrow.now(), o, sid)


class EventCallback:
    """
    a callback combined with an event

    if the `handler` returns a truthy value,
    this class will `set` the event indicating to any waiters that they can proceed
    """

    def __init__(self, handler: HandlerType, timeout_secs: Optional[float] = None):
        self._handler = handler
        self._ready = asyncio.Event()
        self._timeout_secs = timeout_secs
        self._start = None

    async def wait(self):
        return await asyncio.wait_for(self._ready.wait(), self._timeout_secs)

    def clear(self):
        self._ready.clear()

    async def __call__(self, sp: SubPayload):
        if await self._handler(sp):
            self._ready.set()

    def __await__(self):
        return self.wait().__await__()


class UnchangedValue:
    """useful for determining when something is done, say, moving"""

    def __init__(self):
        self._prev: Optional[SubPayload] = None

    __call__: HandlerType

    async def __call__(self, sp: SubPayload):
        prev, self._prev = self._prev, sp
        with suppress(AttributeError):
            return prev.data.message.value == sp.data.message.value


print(_high_to_low_level_sub_map)


def __main():
    pass


if __name__ == '__main__':
    __main()
