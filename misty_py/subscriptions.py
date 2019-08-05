import asyncio
from enum import Enum
from typing import NamedTuple, Set, Optional, Callable, Awaitable, FrozenSet

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
    def event_condition(self) -> EventCondition:
        return EventCondition('sensorId', self.value)


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
    def event_condition(self) -> EventCondition:
        return EventCondition('sensorPosition', self.value)


class Bump(Sensor):
    """sensor that indicates whether you hit something"""
    front_right = 'bfr'
    front_left = 'bfl'
    back_right = 'bbr'
    back_left = 'bbl'


class Actuator(Sensor):
    """sensor that monitors the various possitions of the head and arms"""
    pitch = 'ahp'
    yaw = 'ahy'
    roll = 'ahr'
    left_arm = 'ala'
    right_arm = 'ara'


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

    def __init__(self, handler: HandlerType):
        self._handler = handler
        self._ready = asyncio.Event()

    async def __call__(self, sd: SubData):
        if await self._handler(sd):
            self._ready.set()

    async def wait(self):
        await self._ready.wait()

    def reset(self):
        self._ready.clear()


def __main():
    pass


if __name__ == '__main__':
    __main()
