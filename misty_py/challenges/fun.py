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


async def random_simpsons_quote():
    fn = f'simpsons_{choice(range(1, 101))}.mp3'
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


async def whats_happening():
    # res = await api.audio.play('from_google.mp3', volume=10, blocking=True, how_long_secs=100)
    # res = await api.audio.play('tada_win31.mp3', volume=80, blocking=True, how_long_secs=.5)
    # res = await api.audio.play('tada_win31.mp3', volume=80, blocking=True, how_long_secs=.5)
    # res = await api.audio.play('tada_win31.mp3', volume=80, blocking=True, how_long_secs=4)
    # res = await api.audio.play('tada_win31.mp3', volume=80, blocking=True, how_long_secs=.5)
    res = await api.audio.play('smooth_jazz_speech.mp3', volume=80, blocking=True)
    res = await api.audio.play('smooth_jazz_will_be_deployed.mp3', volume=80, blocking=True)
    # res = await api.audio.play('tada_win31.mp3', volume=80, blocking=True, how_long_secs=.5)

    print(arrow.utcnow())
    return res


async def wait_play():
    coros = (asyncio.sleep(n) for n in range(1, 100))
    d, p = await wait_first(*coros)
    print(type(d), d)
    print(len(p))


def _get_random(v):
    return 2 * v * random() - v


async def _run_n(coro: Callable[[], Awaitable[None]], n_times, sleep_time=.4):
    for _ in range(n_times):
        await coro()
        await asyncio.sleep(sleep_time)


async def move_head(pitch_max=20, roll_max=20, yaw_max=20, velocity=50, n_times=6):
    async def _move():
        await api.movement.move_head(pitch=_get_random(pitch_max), roll=_get_random(roll_max),
                                     yaw=_get_random(yaw_max), velocity=velocity)

    await _run_n(_move, n_times)


async def move_arms(l_max=50, r_max=50, velocity=60, n_times=6):
    async def _move():
        await api.movement.move_arms(l_position=_get_random(l_max), r_position=_get_random(r_max), l_velocity=velocity,
                                     r_velocity=velocity)

    await _run_n(_move, n_times)


async def play(fn, how_long=None, n_times=20):
    async def cancel(_g):
        with suppress(asyncio.CancelledError):
            _g.cancel()
            await _g

    await api.movement.move_head(0, 0, 0, velocity=40)
    p = asyncpartial(api.audio.play, blocking=True)
    await p('smooth_jazz_will_be_deployed.mp3')
    g = asyncio.gather(move_head(velocity=100, roll_max=50, n_times=n_times), move_arms(n_times=n_times))
    coros = (
        wait_for_group(
            p('smooth_jazz.mp3'),
            api.images.display('e_Love.jpg'),
            wait_in_order(
                asyncio.sleep(8.5),
                cancel(g),
                api.images.display('e_Sleeping.jpg'),
                wait_for_group(
                    api.movement.move_head(-100, velocity=4),
                    api.movement.move_arms(l_position=-80, r_position=-80, l_velocity=30, r_velocity=4),
                ),
            ),
        ),
        asyncio.sleep(4),
        api.images.display('e_DefaultContent.jpg'),
    )

    return await wait_in_order(*coros)


async def eyes_wont_set():
    pos = 80
    await asyncio.gather(
        api.images.display('e_Sleeping.jpg'),
        api.movement.move_head(pos, velocity=20),
    )
    await asyncio.sleep(2)
    await api.images.display('e_DefaultContent.jpg')


if __name__ == '__main__':
    async_run(play('jeb'))
    # async_run(eyes_wont_set())
    # async_run(whats_happening())
    # print(arrow.utcnow())
    # asyncio.run(whats_happening())
    # print(arrow.utcnow())
