from __future__ import annotations

import asyncio
from asyncio import create_task
from contextlib import asynccontextmanager
from itertools import count
from typing import Dict, NamedTuple, Union

import websockets

from misty_py.subscriptions import SubType, SubReq, SubPayload, HandlerType, Sub, LLSubType
from .utils import json_obj
from .utils.core import InstanceCache

__author__ = 'acushner'


class TaskInfo(NamedTuple):
    """info about a running task and its associated websocket"""
    task: asyncio.Task
    ws: websockets.WebSocketClientProtocol


async def debug_handler(sp: SubPayload):
    print(sp)


class MistyWS(metaclass=InstanceCache):
    """class that manages websocket interactions with misty"""
    _count = count(1)

    def __init__(self, misty_api):
        from .api import MistyAPI
        self.api: MistyAPI = misty_api
        self._endpoint = self._init_endpoint(self.api.ip)
        self._tasks: Dict[SubReq, TaskInfo] = {}

    @staticmethod
    def _init_endpoint(url):
        res = f'{url.replace("http", "ws", 1)}/pubsub'
        return res

    def _next_sub_id(self) -> int:
        return next(self._count)

    async def subscribe(self, sub: Union[SubType, LLSubType, Sub], handler: HandlerType = debug_handler,
                        debounce_ms: int = 250) -> SubReq:
        """
        subscribe to events from misty

        handler will be invoked every time an event is received
        """
        if isinstance(sub, SubType):
            coros = (self.subscribe(s, handler, debounce_ms) for s in sub.lower_level_subs)
            return await asyncio.gather(*coros)
        if isinstance(sub, LLSubType):
            sub = sub.sub
        sub_req = SubReq.create(sub, self.api)

        ws = await websockets.connect(self._endpoint)
        self._tasks[sub_req] = TaskInfo(asyncio.create_task(self._handle(ws, handler, sub_req)), ws)

        payload = json_obj(Operation='subscribe', Type=sub.sub.value, DebounceMS=debounce_ms,
                           EventName=sub_req.event_name)
        if sub_req.type.ec:
            payload.EventConditions = [ec.json for ec in sub_req.type.ec]
        if sub_req.type.return_prop:
            payload.ReturnProperty = sub_req.type.return_prop
        print(payload)
        await ws.send(payload.json_str)

        return sub_req

    async def subscribe_all(self, handler: HandlerType, debounce_ms=2000):
        """subscribe to everything with no event conditions"""
        coros = (self.subscribe(sub, handler=handler, debounce_ms=debounce_ms) for sub in SubType)
        return await asyncio.gather(*coros)

    async def unsubscribe(self, sub_req: Union[SubType, SubReq]):
        """
        tell misty to stop sending events for this subscription and close the websocket

        can unsubscribe either by `SubType` or `SubReq`
        """
        if isinstance(sub_req, SubType):
            coros = (self.unsubscribe(si) for si in self._tasks if si.type is sub_req)
            return await asyncio.gather(*coros)

        try:
            ti = self._tasks.pop(sub_req)
        except KeyError:
            return False

        ti.task.cancel()

        payload = json_obj(Operation='unsubscribe', EventName=sub_req.event_name, Message=str(sub_req))
        await ti.ws.send(payload.json_str)
        await ti.ws.close()
        return True

    async def unsubscribe_all(self):
        """cancel all active subscriptions"""
        coros = (sr.unsubscribe() for sr in self._tasks)
        return await asyncio.gather(*coros)

    @asynccontextmanager
    async def sub_unsub(self, sub: Union[SubType, LLSubType, Sub], handler: HandlerType, debounce_ms: int = 250) -> SubReq:
        """
        context manager to subscribe to an event, wait for something, and, when the exec block's done, unsubscribe
        useful, e.g., for making things blocking
        """
        sub_req = await self.subscribe(sub, handler, debounce_ms)
        try:
            yield sub_req
        finally:
            create_task(self.unsubscribe(sub_req))

    async def _handle(self, ws, handler: HandlerType, sub_req):
        """
        take messages from the websocket and pass them on to the handler
        additionally, skip the registration message
        TODO: check for error on subscription registration
        """
        async for msg in ws:
            o = json_obj.from_str(msg)

            # skip registration message
            if isinstance(o.message, str):
                print(o.message)
                continue

            sp = self.api.subscription_data[sub_req.type] = SubPayload.from_data(o, sub_req)
            create_task(handler(sp))
