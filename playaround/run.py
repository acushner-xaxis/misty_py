import asyncio

import arrow
import uvloop

from misty_py.api import MistyAPI
from misty_py.misty_ws import MistyWS
from misty_py.subscriptions import SubType, SubId, SubPayload
from misty_py.utils import json_obj, RGB, HeadSettings

# print(json_obj(dict(a=4)))
# t = json_obj([dict(a=4, b=[dict(ab=84, hm=53)]), dict(b=5, c=67)])
t = json_obj([dict(a=4, b=[8, 7, [12, dict(ahoe=234)]]), dict(b=5, c=67, e=dict(a=5))])
t = json_obj()

x = t.tuse = 4
print(x)
# t = json_obj(dict(a=dict(b=4)))
t = t
print(t)
# print(json_obj())
# print(json_obj(dict(a=5), b=6))
# print(json_obj([4, 5]))

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
    sub_id = await mws.subscribe(SubType.self_state, handler, debounce_ms=2000)
    await asyncio.sleep(10)
    await mws.unsubscribe(sub_id)


async def cxl_test():
    async def helper(sleep_time=4):
        print('in here')
        await asyncio.sleep(sleep_time)

    t = asyncio.create_task(helper())
    await asyncio.sleep(0)
    t.cancel()
    # await t


async def handler(sp: SubPayload):
    print(sp)


async def c_test():
    c = C()
    print(c.t)


# c = C()
# print(c.t)

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
print(mws.api.subscription_data[SubType.self_state])
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
