import os
import random
from contextlib import suppress
from pathlib import Path

import arrow

from misty_py.api import MistyAPI
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

    zip = path + 'misty.zip'
    with suppress(FileNotFoundError):
        os.remove(zip)
    os.system(f'zip {zip} {di} {l}')
    print('created', zip)


def search():
    """have misty look around and scan her environment"""


def nod(yaw=0, n_times=4):
    """have misty nod up and down"""


def shake_head(pitch=0):
    """have misty shake head left to right"""


def blinky():
    """make a super blinky eye image out of an existing one"""
