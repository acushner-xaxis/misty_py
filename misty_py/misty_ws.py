from __future__ import annotations

import asyncio
from asyncio import create_task
from contextlib import asynccontextmanager
from enum import Enum
from itertools import count
from typing import Callable, Awaitable, Dict, NamedTuple

import arrow
import websockets

from .utils import json_obj
from .utils.datastructures import InstanceCache

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


class SubInfo(NamedTuple):
    """identifying information about a particular subscription"""
    id: int
    type: Sub
    handler: HandlerType

    @property
    def event_name(self) -> str:
        return f'{self.type.value}_{self.id:04}'


class SubData(NamedTuple):
    """payload from an active subscription"""
    time: arrow.Arrow
    data: json_obj
    sub_info: SubInfo

    @classmethod
    def from_data(cls, o: json_obj, si: SubInfo):
        return cls(arrow.now(), o, si)


class TaskInfo(NamedTuple):
    """info about a running task and its associated websocket"""
    task: asyncio.Task
    ws: websockets.WebSocketClientProtocol


HandlerType = Callable[[SubData], Awaitable[None]]


class MistyWS(metaclass=InstanceCache):
    _count = count(1)

    def __init__(self, misty_api):
        from .api import MistyAPI
        self.api: MistyAPI = misty_api
        self._endpoint = self._init_endpoint(self.api.ip)
        self._tasks: Dict[SubInfo, TaskInfo] = {}

    @staticmethod
    def _init_endpoint(url):
        res = f'{url.replace("http", "ws", 1)}/pubsub'
        print(res)
        return res

    def _next_sub_id(self) -> int:
        return next(self._count)

    async def subscribe(self, sub: Sub, handler: HandlerType, debounce_ms: int = 250) -> SubInfo:
        sub_info = SubInfo(self._next_sub_id(), sub, handler)
        payload = json_obj(Operation='subscribe', Type=sub.value, DebounceMS=debounce_ms, EventName=sub_info.event_name)

        ws = await websockets.connect(self._endpoint)
        self._tasks[sub_info] = TaskInfo(asyncio.create_task(self._handle(ws, handler, sub_info)), ws)
        print(sub_info)
        await ws.send(payload.json_str)

        return sub_info

    async def unsubscribe(self, sub_info: SubInfo):
        try:
            ti = self._tasks[sub_info]
        except KeyError:
            return False

        del self._tasks[sub_info]
        ti.task.cancel()

        payload = json_obj(Operation='unsubscribe', EventName=sub_info.event_name, Message=str(sub_info))
        await ti.ws.send(payload.json_str)
        await ti.ws.close()
        return True

    @asynccontextmanager
    async def sub_unsub(self, sub: Sub, handler: HandlerType, debounce_ms: int = 250) -> SubInfo:
        """
        context manager to subscribe to an event, wait for something, and, when the exec block's done, unsubscribe
        useful, e.g., for starting up slam sensors and waiting for them to be ready
        """
        sub_info = await self.subscribe(sub, handler, debounce_ms)
        try:
            yield sub_info
        finally:
            create_task(self.unsubscribe(sub_info))

    async def _handle(self, ws, handler: HandlerType, sub_info):
        async for msg in ws:
            o = json_obj.from_str(msg)
            sd = self.api.subscription_data[sub_info.type] = SubData.from_data(o, sub_info)
            create_task(handler(sd))
