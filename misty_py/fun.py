import asyncio
import os
import random
from contextlib import suppress
from pathlib import Path

import arrow

from misty_py.api import MistyAPI
from misty_py.subscriptions import Actuator, UnchangedValue, EventCallback
from misty_py.utils import MISTY_URL

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

    zip_path = path + 'misty.zip'
    with suppress(FileNotFoundError):
        os.remove(zip_path)
    os.system(f'zip {zip_path} {di} {l}')
    print('created', zip_path)


def search():
    """have misty look around and scan her environment"""


async def nod(pitch=100, roll=0, yaw=0, velocity=100, n_times=6):
    """have misty nod up and down"""
    for _ in range(n_times):
        print(pitch)
        await api.movement.move_head(pitch=pitch, yaw=yaw, roll=roll, velocity=velocity)
        await asyncio.sleep(.2)
        pitch *= -1


async def shake_head(pitch=20, roll=0, yaw=-40, velocity=100, n_times=6):
    """have misty shake head left and right"""
    for _ in range(n_times):
        print(yaw)
        await api.movement.move_head(pitch=pitch, yaw=yaw, roll=roll, velocity=velocity)
        await asyncio.sleep(.3)
        yaw *= -1


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
