from __future__ import annotations

import asyncio
from asyncio import create_task
from contextlib import asynccontextmanager, suppress
from itertools import count
from typing import Dict, NamedTuple, Union, Optional, List

import arrow
import websockets

from misty_py.subscriptions import SubType, SubId, SubPayload, HandlerType, Sub, LLSubType
from .utils import json_obj
from .utils.core import InstanceCache

__author__ = 'acushner'


class TaskInfo(NamedTuple):
    """info about a running task and its associated websocket"""
    task: asyncio.Task
    ws: websockets.WebSocketClientProtocol


class EventCallback:
    """
    a callback combined with an event

    if the `handler` returns a truthy value,
    this class will `set` the event indicating to any waiters that they can proceed
    """

    def __init__(self, handler: HandlerType, timeout_secs: Optional[float] = None):
        self._handler = handler
        self._ready = asyncio.Event()
        self._timeout_secs = timeout_secs

    async def wait(self):
        try:
            return await asyncio.wait_for(self._ready.wait(), self._timeout_secs)
        except asyncio.CancelledError:
            self.set()

    def clear(self):
        self._ready.clear()

    def set(self):
        self._ready.set()

    async def __call__(self, sp: SubPayload):
        if await self._handler(sp):
            self._ready.set()

    async def sub_unsub(self, api, sub: Union[SubType, LLSubType, Sub], debounce_ms: int = 250):
        try:
            async with api.ws.sub_unsub(sub, self, debounce_ms):
                await self
        except asyncio.CancelledError:
            self.set()

    def __await__(self):
        return self.wait().__await__()


class UnchangedValue:
    """useful for determining when something is done, say, moving"""

    def __init__(self, tolerance: float = 0.0, *, debug=False):
        self._prev: Optional[SubPayload] = None
        self._init_val: Optional[float] = None
        self._tolerance = abs(tolerance)
        self.debug = debug

    __call__: HandlerType

    async def __call__(self, sp: SubPayload):
        prev, self._prev = self._prev, sp
        with suppress(AttributeError):
            p, c = prev.data.message.value, sp.data.message.value
            if self._init_val is None:
                self._init_val = p
            if self.debug:
                print(f'prev: {prev.data.message.pretty}, cur: {sp.data.message.pretty}')
            return abs(p - c) < self._tolerance and p != self._init_val

    def clear(self):
        self._init_val = None


class EventCBUnchanged(EventCallback):
    def __init__(self, tolerance: float = 0.0, *, debug=False, timeout_secs: Optional[float] = None):
        self._uv = UnchangedValue(tolerance, debug=debug)
        super().__init__(self._uv, timeout_secs)

    def clear(self):
        super().clear()
        self._uv.clear()


async def debug_handler(sp: SubPayload):
    print(sp)


class SubscriptionError(Exception):
    """represent failed subscription to misty"""


class MistyWS(metaclass=InstanceCache):
    """class that manages websocket interactions with misty"""
    _count = count(1)

    def __init__(self, misty_api):
        from .api import MistyAPI
        self.api: MistyAPI = misty_api
        self._endpoint = self._init_endpoint(self.api.ip)
        self._tasks: Dict[SubId, TaskInfo] = {}

    @staticmethod
    def _init_endpoint(url):
        return f'{url.replace("http", "ws", 1)}/pubsub'

    async def _send(self, payload: json_obj):
        """simple function to send a bespoke payload via a websocket. useful for debugging"""
        ws = await websockets.connect(self._endpoint)
        return await ws.send(payload.json_str)

    def _next_sub_id(self) -> int:
        return next(self._count)

    async def subscribe(self, sub: Union[SubType, LLSubType, Sub], handler: HandlerType = debug_handler,
                        debounce_ms: int = 250) -> Union[SubId, List[SubId]]:
        """
        subscribe to events from misty

        handler will be invoked every time an event is received
        """
        if isinstance(sub, SubType):
            coros = (self.subscribe(s, handler, debounce_ms) for s in sub.lower_level_subs)
            return await asyncio.gather(*coros)

        if isinstance(sub, LLSubType):
            sub = sub.sub

        sub_id = SubId.create(sub, self.api)
        ws = await websockets.connect(self._endpoint)
        self._tasks[sub_id] = TaskInfo(asyncio.create_task(self._handle(ws, handler, sub_id)), ws)

        payload = sub_id.to_json(debounce_ms)
        print('subscribing:', payload)
        await ws.send(payload.json_str)

        return sub_id

    async def subscribe_all(self, handler: HandlerType, debounce_ms=2000):
        """subscribe to everything with no event conditions"""
        coros = (self.subscribe(sub, handler=handler, debounce_ms=debounce_ms) for sub in SubType)
        return await asyncio.gather(*coros)

    async def _unsubscribe_str(self, s: str):
        payload = json_obj(Operation='unsubscribe', EventName=s, Message=s)
        await self._send(payload)
        return True

    async def unsubscribe(self, sub_id: Union[SubType, SubId, str]):
        """
        tell misty to stop sending events for this subscription and close the websocket

        can unsubscribe either by `SubType`, `SubId`, or str containing the event_name
        """
        print(arrow.utcnow(), 'unsubscribing:', sub_id)
        if isinstance(sub_id, str):
            return await self._unsubscribe_str(sub_id)

        if isinstance(sub_id, SubType):
            coros = (self.unsubscribe(si) for si in self._tasks if si.sub.sub_type is sub_id)
            return await asyncio.gather(*coros)

        try:
            ti = self._tasks.pop(sub_id)
        except KeyError:
            return False

        ti.task.cancel()

        payload = json_obj(Operation='unsubscribe', EventName=sub_id.event_name, Message=str(sub_id))
        await ti.ws.send(payload.json_str)
        await ti.ws.close()
        print(arrow.utcnow(), 'unsubscribed')
        return True

    async def unsubscribe_all(self):
        """cancel all active subscriptions"""
        coros = (sid.unsubscribe() for sid in self._tasks)
        return await asyncio.gather(*coros)

    @asynccontextmanager
    async def sub_unsub(self, sub: Union[SubType, LLSubType, Sub], handler: HandlerType,
                        debounce_ms: int = 250) -> Union[SubId, SubType]:
        """
        context manager to subscribe to an event, wait for something, and, when the exec block's done, unsubscribe
        useful, e.g., for making things blocking
        """
        sub_id_or_ids = await self.subscribe(sub, handler, debounce_ms)
        try:
            yield sub_id_or_ids
        finally:
            if not isinstance(sub_id_or_ids, list):
                sub_id_or_ids = [sub_id_or_ids]
            for sid in sub_id_or_ids:
                create_task(self.unsubscribe(sid))

    async def _handle(self, ws, handler: HandlerType, sub_id):
        """
        take messages from the websocket and pass them on to the handler
        additionally, skip the registration message
        """
        async for msg in ws:
            o = json_obj.from_str(msg)

            # skip registration message
            if isinstance(o.message, str):
                if o.message.startswith('Registration Status: API event registered'):
                    continue

                print('Failed to register:', o)
                await sub_id.unsubscribe()
                raise SubscriptionError(f'failed to subscribe: {msg}')

            sp = self.api.subscription_data[sub_id.sub] = SubPayload.from_data(o, sub_id)
            create_task(handler(sp))
