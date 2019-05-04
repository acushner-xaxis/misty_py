import asyncio
import random
from enum import Enum
from functools import partial

import arrow
import websockets
import uvloop

uvloop.install()


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

    @classmethod
    def random(cls):
        return random.choice(cls._list_cls).value


Sub._list_cls = list(Sub)


async def echo(websocket, path):
    print(type(websocket), websocket, type(path), path)
    async for m in websocket:
        await websocket.send(m)


async def stream(websocket, path, sleep_time=1.0):
    while True:
        await websocket.send(Sub.random())
        await asyncio.sleep(sleep_time)


async def handler(websocket, path):
    streamer = asyncio.ensure_future(stream(websocket, path, 1.0))
    echoer = asyncio.ensure_future(echo(websocket, path))

    done, pending = await asyncio.wait([streamer, echoer], return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()


loop = asyncio.get_event_loop()
loop.run_until_complete(websockets.serve(echo, 'localhost', 8898))
# loop.run_until_complete(websockets.serve(partial(stream, sleep_time=1.0), 'localhost', 8898))
# loop.run_until_complete(websockets.serve(handler, 'localhost', 8898))
loop.run_forever()
