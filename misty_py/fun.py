import asyncio
import os
import random
from contextlib import suppress
from pathlib import Path

import arrow

from misty_py.api import MistyAPI
from misty_py.subscriptions import Actuator
from misty_py.misty_ws import EventCallback, UnchangedValue
from misty_py.utils import MISTY_URL, wait_first

__author__ = 'acushner'

api = MistyAPI(MISTY_URL)


async def random_simpsons_quote():
    fn = f'simpsons_{random.choice(range(1, 101))}.mp3'
    print(fn)
    await api.audio.play(fn)


async def dump_debug_info():
    cur_date = arrow.now().format('YYYYMMDD')
    path = f'/tmp/{cur_date}.cushner.'
    t = await api.system.device_info
    di = path + 'device_info'
    with open(di, 'w') as f:
        f.write(t.pretty)

    t = await api.system.get_logs(arrow.utcnow().shift(hours=-7))
    l = path + 'log'
    with open(l, 'w') as f:
        f.write(t)

    z = path + 'misty.zip'
    with suppress(FileNotFoundError):
        os.remove(z)
    os.system(f'zip {z} {di} {l}')
    print('created', z)


def search():
    """have misty look around and scan her environment"""


async def nod(pitch=100, roll=0, yaw=0, velocity=100, n_times=6):
    """have misty nod up and down"""
    for _ in range(n_times):
        print(pitch)
        await api.movement.move_head(pitch=pitch, yaw=yaw, roll=roll, velocity=velocity)
        await asyncio.sleep(.2)
        pitch *= -1
    await api.movement.move_head(pitch=0)


async def shake_head(pitch=20, roll=0, yaw=-40, velocity=100, n_times=6):
    """have misty shake head left and right"""
    for _ in range(n_times):
        print(yaw)
        await api.movement.move_head(pitch=pitch, yaw=yaw, roll=roll, velocity=velocity)
        await asyncio.sleep(.3)
        yaw *= -1
    await api.movement.move_head(yaw=0)


async def wave(l_or_r: str = 'r', position=60, velocity=60, n_times=6):
    positions = position, 0
    for i in range(n_times):
        kwargs = {f'{l_or_r}_position': position, f'{l_or_r}_velocity': velocity}
        await api.movement.move_arms(**kwargs)
        await asyncio.sleep(.4)
        position = positions[i & 1]
    await api.movement.move_arms(l_position=0, r_position=0, l_velocity=velocity, r_velocity=velocity)


async def wave2(l_or_r: str = 'l', position=120, velocity=60, n_times=8):
    positions = position, 0
    uv = UnchangedValue(5, debug=True)
    ecb = EventCallback(uv)
    async with api.ws.sub_unsub(Actuator.left_arm, ecb, 10):
        for i in range(n_times):
            position = positions[i & 1]
            kwargs = {f'{l_or_r}_position': position, f'{l_or_r}_velocity': velocity}
            await api.movement.move_arms(**kwargs)
            ecb.clear()
            uv.clear()
            await ecb
            print(position)
    await api.movement.move_arms(l_position=0, r_position=0, l_velocity=velocity, r_velocity=velocity)


async def blinky():
    """make a super blinky eye image out of an existing one"""


async def train_face():
    """
    create a clean routine for training someone's face
    - respond to misty command?
    - take picture to confirm who's face it is
    - change led colors while training
    - display countdown on screen
    - prompt for name at end and translate into text?
    - save picture with name
    - ultimately a simple website with form to add cool things about the person?
    """


async def whats_happening():
    res = await api.audio.play('from_google.mp3', volume=10, blocking=True)
    res = await api.audio.play('tada_win31.mp3', volume=80, blocking=True)
    print(res)
    print(arrow.utcnow())
    return res


async def wait_play():
    coros = (asyncio.sleep(n) for n in range(1, 100))
    d, p = await wait_first(*coros)
    print(type(d), d)
    print(len(p))


if __name__ == '__main__':
    print(asyncio.run(wait_play()))
    # asyncio.run(whats_happening())
    # print(arrow.utcnow())
