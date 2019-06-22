import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
import arrow

import websockets

from misty_py.utils import json_obj

pool = ThreadPoolExecutor(8)


async def hello(uri):
    rie = partial(asyncio.get_event_loop().run_in_executor, pool)

    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello world!")
        async for message in websocket:
            await websocket.send(await rie(input))


async def subscribe(uri):
    async with websockets.connect(uri) as ws:
        async for msg in ws:
            t = json_obj.from_str(msg)
            print(t.Type)


# asyncio.ensure_future(hello('ws://localhost:8898/jebtuse'))

asyncio.get_event_loop().run_until_complete(subscribe('ws://localhost:8898/jebtuse'))
