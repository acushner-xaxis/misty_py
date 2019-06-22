import asyncio

import arrow
import uvloop

from misty_py.api import MistyAPI
from misty_py.misty_ws import MistyWS, Sub, SubInfo, SubData
from misty_py.utils import json_obj, RGB, HeadSettings

print(HeadSettings(yaw=40).json)
sys.exit

api = MistyAPI('localhost:9999')

uvloop.install()
mws = MistyWS(api)
mws2 = MistyWS(api)
print(mws is mws2)

print(RGB.from_hex(0xFFFFFF).hex)


class C:
    def __init__(self):
        self.t = asyncio.run(self.atest())
        print(self.t)

    async def atest(self):
        print('in')
        await asyncio.sleep(1)
        print('done')
        return 4


async def run():
    sub_info = await mws.subscribe(Sub.self_state, handler, debounce_ms=2000)
    await asyncio.sleep(10)
    await mws.unsubscribe(sub_info)


async def cxl_test():
    async def helper(sleep_time=4):
        print('in here')
        await asyncio.sleep(sleep_time)

    t = asyncio.create_task(helper())
    await asyncio.sleep(0)
    t.cancel()
    # await t


async def handler(sd: SubData):
    print(sd)


async def c_test():
    c = C()
    print(c.t)


# c = C()
# print(c.t)

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
print(mws.api.subscription_data[Sub.self_state])
# loop.run_until_complete(cxl_test())
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
