import asyncio
import os
from random import choice, random
from contextlib import suppress
from typing import Callable, Awaitable, NamedTuple

import arrow

from misty_py.api import MistyAPI
from misty_py.subscriptions import Actuator, Touch, SubType, SubPayload, LLSubType
from misty_py.misty_ws import EventCallback, UnchangedValue
from misty_py.utils import wait_first, asyncpartial, wait_in_order, wait_for_group
from misty_py.utils.core import async_run

__author__ = 'acushner'

api = MistyAPI()


def search():
    """have misty look around and scan her environment"""


async def play():
    # print(await api.movement.get_actuator_values())
    # return
    async def _handler(sp: SubPayload):
        t = LLSubType.from_sub_payload(sp)
        print(type(t), t)

    async with api.ws.sub_unsub(SubType.touch_sensor, _handler):
        await asyncio.sleep(20)


class PRY(NamedTuple):
    pitch: int = 0
    roll: int = 0
    yaw: int = 0

    @property
    def json(self):
        return self._asdict()

    def __mul__(self, other):
        return PRY(*(other * v for v in self))

    def __rmul__(self, other):
        return self * other


touch_response = {
    Touch.chin: PRY(pitch=-1),
    Touch.chin_left: PRY(-1, 1, -1),
    Touch.chin_right: PRY(-1, -1, 1),
    Touch.head_back: PRY(pitch=1),
    Touch.head_front: PRY(pitch=-1),
    Touch.head_left: PRY(1, -1, 1),
    Touch.head_right: PRY(1, 1, -1),
    Touch.head_top: PRY(),
    Touch.scruff: PRY(-4, -4, -4),
}

if __name__ == '__main__':
    # class A:
    #     @cached_property
    #     def tuse(self):
    #         print('tuse')
    #         return 42
    #
    #     @cached_classproperty
    #     def jebson(cls):
    #         print('jebson')
    #         return 91
    #
    # print(A.jebson, A.jebson, A.jebson)
    # a = A()
    # print(a.tuse, a.tuse, a.tuse, a.jebson)
    asyncio.run(play())

    # async_run(eyes_wont_set())
    # async_run(whats_happening())
    # print(arrow.utcnow())
    # asyncio.run(whats_happening())
    # print(arrow.utcnow())
