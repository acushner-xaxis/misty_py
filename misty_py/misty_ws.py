from __future__ import annotations
import asyncio
from asyncio import Task
from collections import defaultdict
from enum import Enum
from itertools import count
from typing import Callable, Awaitable, Dict, NamedTuple, Set

import websockets

from utils import json_obj
from utils.datastructures import Singleton

__author__ = 'acushner'


class TouchSensor(Enum):
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
    def full_value(self):
        return f'CapTouch_{self.value}'


class BumpSensor(Enum):
    front_right = 'bfr'
    front_left = 'bfl'
    back_right = 'bbr'
    back_left = 'bbl'


class Sub(Enum):
    time_of_flight = 'TimeOfFlight'
    face_recognition = 'FaceRecognition'
    locomotion_command = 'LocomotionCommand'
    halt_command = 'HaltCommand'
    self_state = 'SelfState'
    world_state = 'WorldState'
    actuator_position = 'ActuatorPosition'
    bump_sensor = 'BumpSensor'
    drive_encoders = 'DriveEncoders'
    touch_sensor = 'TouchSensor'
    imu = 'IMU'
    serial_message = 'SerialMessage'
    audio_play_complete = 'AudioPlayComplete'


class SubscriptionInfo(NamedTuple):
    id: int
    type: Sub
    handler: handler_type

    @property
    def event_name(self) -> str:
        return f'{self.type.value}_{self.id:04}'


handler_type = Callable[[json_obj, SubscriptionInfo], Awaitable[None]]


class _Subscriptions:
    _count = count(1)

    def __init__(self):
        self._event_name_to_si: Dict[str, SubscriptionInfo] = {}
        self._type_to_sis: Dict[Sub, Set[SubscriptionInfo]] = defaultdict(set)

    def subscribe(self, sub: Sub, handler: handler_type) -> SubscriptionInfo:
        si = SubscriptionInfo(self._next_sub_id(), sub, handler)
        self._event_name_to_si[si.event_name] = si
        self._type_to_sis[si.type].add(si)
        return si

    def unsubscribe(self, sub_info: SubscriptionInfo) -> bool:
        """return True if should unsubscribe from feed"""
        del self._event_name_to_si[sub_info.event_name]
        event_type_subs = self._type_to_sis[sub_info.type]
        event_type_subs.remove(sub_info)
        return not event_type_subs

    async def handle(self, sub: Sub, msg: json_obj):
        await asyncio.gather(*(si.handler(msg) for si in self._type_to_sis[sub]))

    def _next_sub_id(self) -> int:
        return next(self._count)


class TaskInfo(NamedTuple):
    task: Task
    ws: websockets.WebSocketClientProtocol


class MistyWS(metaclass=Singleton):
    _count = count(1)

    def __init__(self, ip):
        self.ip = ip
        self._tasks: Dict[SubscriptionInfo, TaskInfo] = {}

    @property
    def _endpoint(self):
        return f'ws://{self.ip}/pubsub'

    def _next_sub_id(self) -> int:
        return next(self._count)

    async def subscribe(self, sub: Sub, handler: handler_type, debounce_ms: int = 250) -> SubscriptionInfo:
        sub_info = SubscriptionInfo(self._next_sub_id(), sub, handler)
        payload = json_obj(Operation='subscribe', Type=sub.value, DebounceMS=debounce_ms, EventName=sub_info.event_name)

        ws = await websockets.connect(self._endpoint)
        self._tasks[sub_info] = TaskInfo(asyncio.create_task(self._handle(ws, handler, sub_info)), ws)
        await ws.send(payload.json_str)

        return sub_info

    async def unsubscribe(self, sub_info: SubscriptionInfo):
        payload = json_obj(Operation='unsubscribe', EventName=sub_info.event_name, Message=str(sub_info))
        ti = self._tasks[sub_info]
        ti.task.cancel()
        await ti.ws.send(payload.json_str)
        await ti.ws.close()

    @staticmethod
    async def _handle(ws, handler, sub_info):
        async for msg in ws:
            o = json_obj.from_str(msg)
            await handler(o, sub_info)
