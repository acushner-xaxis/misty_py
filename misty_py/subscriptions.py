from __future__ import annotations

import asyncio
from abc import abstractmethod
from contextlib import suppress
from enum import Enum
from typing import NamedTuple, Set, Optional, Callable, Awaitable, FrozenSet, Generator

import arrow

from misty_py.utils import json_obj

__author__ = 'acushner'

HandlerType = Callable[['SubData'], Awaitable[bool]]


class EventCondition(NamedTuple):
    """filter subscription events based on these conditions"""
    name: str
    value: str
    inequality: str = '='

    @property
    def json(self) -> json_obj:
        return json_obj(Property=self.name, Inequality=self.inequality, Value=self.value)


class Sensor(Enum):
    """base enum: represent a sensor on misty"""

    @property
    @abstractmethod
    def _sub_type(self) -> SubType:
        """fill in with the associated subscription type"""

    @property
    def _event_condition(self) -> EventCondition:
        return EventCondition('sensorId', self.value)

    @property
    def sub(self) -> SubEC:
        return SubEC.from_sub_ec(self._sub_type, self._event_condition)

    @classmethod
    def get_all_subscriptions(cls) -> Generator[SubEC]:
        return (s.sub for s in cls)


class Touch(Sensor):
    # TODO: get abbreviated values for `Touch` from misty
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

    @property
    def _sub_type(self) -> SubType:
        return SubType.touch_sensor


class Bump(Sensor):
    """sensor that indicates whether you hit something"""

    front_right = 'bfr'
    front_left = 'bfl'
    back_right = 'bbr'
    back_left = 'bbl'

    @property
    def _sub_type(self) -> SubType:
        return SubType.bump_sensor


class Actuator(Sensor):
    """sensor that monitors the various positions of the head and arms"""
    pitch = 'ahp'
    yaw = 'ahy'
    roll = 'ahr'
    left_arm = 'ala'
    right_arm = 'ara'

    @property
    def _sub_type(self) -> SubType:
        return SubType.actuator_position


class SubType(Enum):
    """represent subscription types"""
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


_sub_type_ec_dict = {}


class SubEC(NamedTuple):
    """combine subscription type with any event conditions you want to use"""
    sub: SubType
    ec: FrozenSet[EventCondition] = frozenset()

    @classmethod
    def from_sub_ec(cls, sub: SubType, *ec: EventCondition):
        return cls(sub, frozenset(ec))


class SubReq(NamedTuple):
    """identifying information about a particular requested subscription"""
    id: int
    type: SubType
    handler: HandlerType
    api: 'MistyAPI'
    event_conditions: FrozenSet[EventCondition]

    @property
    def event_name(self) -> str:
        return f'{self.type.value}_{self.id:04}'

    async def unsubscribe(self):
        await self.api.ws.unsubscribe(self)


class SubData(NamedTuple):
    """payload from an active subscription"""
    time: arrow.Arrow
    data: json_obj
    sub_req: SubReq

    @classmethod
    def from_data(cls, o: json_obj, sr: SubReq):
        return cls(arrow.now(), o, sr)


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

    async def __call__(self, sd: SubData):
        if await self._handler(sd):
            self._ready.set()

    def __await__(self):
        return self.wait().__await__()

    async def wait(self):
        return await asyncio.wait_for(self._ready.wait(), self._timeout_secs)

    def clear(self):
        self._ready.clear()


class UnchangedValue:
    """useful for determining when something is done, say, moving"""

    def __init__(self):
        self._prev: Optional[SubData] = None

    __call__: HandlerType

    async def __call__(self, sd: SubData):
        print('uv', sd)
        prev, self._prev = self._prev, sd
        with suppress(AttributeError):
            return prev.data.message.value == sd.data.message.value


def __main():
    pass


if __name__ == '__main__':
    __main()
