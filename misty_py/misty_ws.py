import asyncio
from collections import defaultdict
from enum import Enum
from itertools import count
from typing import Callable, Awaitable, Dict

import websockets

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


# class _Subscriptions:
#     def __init__(self):
#         self._event_name_to_sub = {}
#         self._sub_to_event_names = defaultdict(set)
#         self._event_name_to_handlers = defaultdict(lambda: defaultdict(int))
#
#     def add_sub(self, sub: Sub, event_name: str, handler: Callable[[Dict], None]):
#         self._event_name_to_sub[event_name] = sub
#         self._event_name_to_handlers[event_name].add(handler)
#         self._sub_to_event_names[sub].add(event_name)
#
#     def rm_sub(self, event_name, handler):
#         """return True if should unsubscribe"""
#         sub = self._event_name_to_sub[event_name]
#         del self._event_name_to_sub[event_name]
#
#         self._sub_to_event_names[sub].remove(event_name)
#
#         handlers = self._event_name_to_handlers[event_name]
#         handlers[handler] -= 1
#         return not handlers


class _Subscriptions:
    """assume one handler per sub"""

class MistyWS:
    _count = count()
    def __init__(self, ip):
        self.ip = ip
        self._subscriptions = _Subscriptions()

    @property
    def _endpoint(self):
        return f'http://{self.ip}/pubsub'

    def subscribe(self, sub: Sub, handler: Callable[[Dict], None], debounce_ms: int = 250):
        asyncio.run(self.a_subscribe(sub, handler, debounce_ms))

    async def a_subscribe(self, sub: Sub, handler: Callable[[Dict], None], debounce_ms: int = 250):
        event_name = str(next(self._count))
        payload = dict(Operation='subscribe', Type=sub.value, DebounceMS=debounce_ms, EventName=event_name)
        self._subscriptions.add_sub(sub, event_name, handler)
        async with websockets.connect(self._endpoint) as ws:
            await ws.send(payload)
        return event_name


    def unsubscribe(self, event_name: str, handler):
        self._subscriptions.rm_sub(event_name, handler)
        handlers = self._subscriptions[event_name]
        handlers.remove()

    async def handle(self, msg):
        async with websockets.connect(self._endpoint) as ws:
            async for msg in ws:
