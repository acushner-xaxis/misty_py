import asyncio

from api import MistyAPI
from utils import json_obj

api = MistyAPI('1.2.3.4')
print(id(api.images))
print(id(api.images))


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
