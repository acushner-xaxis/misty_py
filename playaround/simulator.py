import asyncio
from functools import partial, wraps

import arrow
import websockets

import msgs
from misty_ws import Sub
from utils import json_obj

loop = asyncio.get_event_loop()

handlers = dict()


def register(sub: Sub):
    def deco(func):
        handlers[sub] = func
        return func

    return deco


async def main(ws, path):
    tasks = {}
    if path != '/pubsub':
        return
    async for msg in ws:
        msg = json_obj.from_str(msg)
        if msg.Operation == 'subscribe':
            tasks[msg.EventName] = asyncio.create_task(handlers[Sub(msg.Type)](ws, msg.DebounceMS / 1000))
        elif msg.Operation == 'unsubscribe':
            tasks[msg.EventName].cancel()


@register(Sub.self_state)
async def self_state(ws: websockets.WebSocketServerProtocol, debounce_secs=4):
    while True:
        print(arrow.now())
        await ws.send(msgs.SelfState.json_str)
        await asyncio.sleep(debounce_secs)


loop.run_until_complete(websockets.serve(main, 'localhost', 9999))
loop.run_forever()
