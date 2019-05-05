import asyncio

import arrow
import uvloop

from api import MistyAPI, delay
from misty_ws import MistyWS, Sub, SubscriptionInfo
from utils import json_obj, RGB

api = MistyAPI('1.2.3.4')

uvloop.install()
mws = MistyWS('localhost:9999')
mws2 = MistyWS('localhost:9999')
print(mws is mws2)

print(RGB.from_hex(0xFFFFFF).hex)


async def run():
    sub_info = await mws.subscribe(Sub.self_state, handler, debounce_ms=2000)
    await asyncio.sleep(10)
    await mws.unsubscribe(sub_info)


async def delay_test():
    async def helper():
        print('yo!!!!')

    print(arrow.now())
    t = asyncio.create_task(delay(2, helper()))
    await asyncio.wait_for(t, timeout=1)
    # t.cancel()
    print('tuse')
    print(arrow.now())


async def handler(o: json_obj, sub_info: SubscriptionInfo):
    print(o)
    print(sub_info)


loop = asyncio.get_event_loop()
loop.run_until_complete(delay_test())
# class aobject:
#     async def __new__(cls, *args, **kwargs):
#         instance = super().__new__(cls)
#         await instance.__init__(*args, **kwargs)
#         return instance
#
#     async def __init__(self):
#         pass
#
#
# class A(aobject):
#     async def __init__(self):
#         print('jeb')
#         await asyncio.sleep(2)
#         print('tuse')
#
#
# async def f():
#     await A()
#
# asyncio.run(f())
