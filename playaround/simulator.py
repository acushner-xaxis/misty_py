import asyncio
from functools import partial, wraps

import websockets

import msgs
from misty_ws import Sub
from utils import json_obj

loop = asyncio.get_event_loop()

payload = json_obj(Operation='subscribe', Type=sub.value, DebounceMS=debounce_ms, EventName=sub_info.event_name)

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
            tasks[msg.EventName] = asyncio.create_task(handlers[Sub(msg.Type)](ws))
        elif msg.Operation == 'unsubscribe':
            tasks[msg.EventName].cancel()


@register(Sub.self_state)
async def self_state(ws):
    while True:
        print('running')
        await ws.send(msgs.SelfState)
        await asyncio.sleep(1)


loop.run_until_complete(websockets.serve(main, 'localhost', 9999))
loop.run_forever()
