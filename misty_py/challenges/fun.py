import asyncio
import os
from random import choice, random
from contextlib import suppress
from typing import Callable, Awaitable

import arrow

from misty_py.api import MistyAPI
from misty_py.subscriptions import Actuator
from misty_py.misty_ws import EventCallback, UnchangedValue
from misty_py.utils import wait_first, asyncpartial, wait_in_order, wait_for_group
from misty_py.utils.core import async_run

__author__ = 'acushner'

api = MistyAPI()


def search():
    """have misty look around and scan her environment"""


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


if __name__ == '__main__':
    pass
    # async_run(eyes_wont_set())
    # async_run(whats_happening())
    # print(arrow.utcnow())
    # asyncio.run(whats_happening())
    # print(arrow.utcnow())
