from __future__ import annotations

import asyncio
from asyncio import create_task
from contextlib import asynccontextmanager
from itertools import count
from typing import Dict, NamedTuple, Union

import websockets

from misty_py.subscriptions import Sub, SubReq, SubData, HandlerType, SubEC
from .utils import json_obj
from .utils.core import InstanceCache

__author__ = 'acushner'


class TaskInfo(NamedTuple):
    """info about a running task and its associated websocket"""
    task: asyncio.Task
    ws: websockets.WebSocketClientProtocol


async def debug_handler(sd: SubData):
    print(sd)
    # if isinstance(sd.data.message, json_obj):
    #     with open(f'/tmp/{sd.sub_req.type.name}.json', 'w') as f:
    #         json.dump(sd.data, f)
    # await sd.sub_req.api.ws.unsubscribe(sd.sub_req)


class MistyWS(metaclass=InstanceCache):
    _count = count(1)

    def __init__(self, misty_api):
        from .api import MistyAPI
        self.api: MistyAPI = misty_api
        self._endpoint = self._init_endpoint(self.api.ip)
        self._tasks: Dict[SubReq, TaskInfo] = {}

    @staticmethod
    def _init_endpoint(url):
        res = f'{url.replace("http", "ws", 1)}/pubsub'
        print(res)
        return res

    def _next_sub_id(self) -> int:
        return next(self._count)

    async def subscribe(self, sub_ec: Union[Sub, SubEC], handler: HandlerType = debug_handler,
                        debounce_ms: int = 250) -> SubReq:
        """
        subscribe to events from misty

        handler will be invoked every time an event is received
        """
        if isinstance(sub_ec, Sub):
            sub_ec = SubEC.from_sub_ec(sub_ec)
        sub_req = SubReq(self._next_sub_id(), sub_ec.sub, handler, self.api, sub_ec.ec)

        ws = await websockets.connect(self._endpoint)
        self._tasks[sub_req] = TaskInfo(asyncio.create_task(self._handle(ws, handler, sub_req)), ws)

        payload = json_obj(Operation='subscribe', Type=sub_ec.sub.value, DebounceMS=debounce_ms,
                           EventName=sub_req.event_name)
        if sub_req.event_conditions:
            payload.EventConditions = [ec.json for ec in sub_req.event_conditions]
        print(payload)
        await ws.send(payload.json_str)

        return sub_req

    async def subscribe_all(self, handler: HandlerType, debounce_ms=2000):
        coros = (self.subscribe(sub, handler=handler, debounce_ms=debounce_ms) for sub in Sub)
        return await asyncio.gather(*coros)

    async def unsubscribe(self, sub_req: Union[Sub, SubReq]):
        """
        tell misty to stop sending events for this subscription and close the websocket

        can unsubscribe either by `Sub` or `SubReq`
        """
        if isinstance(sub_req, Sub):
            coros = (self.unsubscribe(si) for si in self._tasks if si.type is sub_req)
            return await asyncio.gather(*coros)

        try:
            ti = self._tasks[sub_req]
        except KeyError:
            return False

        del self._tasks[sub_req]
        ti.task.cancel()

        payload = json_obj(Operation='unsubscribe', EventName=sub_req.event_name, Message=str(sub_req))
        await ti.ws.send(payload.json_str)
        await ti.ws.close()
        return True

    async def unsubscribe_all(self):
        coros = (self.unsubscribe(si) for si in self._tasks)
        return await asyncio.gather(*coros)

    @asynccontextmanager
    async def sub_unsub(self, sub: Union[Sub, SubEC], handler: HandlerType, debounce_ms: int = 250) -> SubReq:
        """
        context manager to subscribe to an event, wait for something, and, when the exec block's done, unsubscribe
        useful, e.g., for starting up slam sensors and waiting for them to be ready
        """
        sub_req = await self.subscribe(sub, handler, debounce_ms)
        try:
            yield sub_req
        finally:
            create_task(self.unsubscribe(sub_req))

    async def _handle(self, ws, handler: HandlerType, sub_req):
        async for msg in ws:
            o = json_obj.from_str(msg)

            # skip registration message
            if isinstance(o.message, str):
                continue

            sd = self.api.subscription_data[sub_req.type] = SubData.from_data(o, sub_req)
            create_task(handler(sd))
