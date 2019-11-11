from __future__ import annotations

import asyncio
import inspect
import os
import textwrap
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import suppress
from functools import partial
from typing import Dict, Optional

import arrow
import requests

from misty_py.apis import *
from misty_py.misty_ws import MistyWS
from misty_py.subscriptions import SubPayload, Sub
from misty_py.utils import *

log = init_log(__name__)

with suppress(ModuleNotFoundError):
    import uvloop

    uvloop.install()

__all__ = ('MistyAPI',)


class MistyAPI(RestAPI):
    """
    asyncio-based REST API for the misty II robot

    - wrap multiple `PartialAPI` objects to access misty
        - for organizational ease
    - handle interacting with websockets
    - a simple usage example

    ==========PartialAPIs============

    {partial_api_section}
    =================================


    ===========websockets============

        `ws` contains access to the websocket interface, used for pub/sub interaction

        `subscription_data` contains the most recent piece of data received from websockets

    =================================



    ==============usage==============

        {usage_section}

    =================================
    """

    _pool = ThreadPoolExecutor(64)

    def __init__(self, ip: Optional[str] = None):
        """either pass in ip directly or set in env"""
        self.ip = self._init_ip(ip)
        self.ws = MistyWS(self)

        # ==============================================================================================================
        # PartialAPIs
        # ==============================================================================================================

        self.images = ImageAPI(self)
        self.audio = AudioAPI(self)
        self.faces = FaceAPI(self)
        self.movement = MovementAPI(self)
        self.system = SystemAPI(self)
        self.navigation = NavigationAPI(self)
        self.skills = SkillAPI(self)

        # ==============================================================================================================
        # SUBSCRIPTION DATA - store most recent subscription info here
        # ==============================================================================================================

        self.subscription_data: Dict[Sub, SubPayload] = {}

    @staticmethod
    def _init_ip(ip):
        ip = ip or os.environ.get('MISTY_IP')
        if not ip:
            raise ValueError('You must provide an ip argument, or set $MISTY_IP in your env')

        if not ip.startswith('http://') or ip.startswith('https://'):
            ip = f'http://{ip}'
        return ip

    # ==================================================================================================================
    # REST CALLS
    # ==================================================================================================================
    def _endpoint(self, endpoint, **params) -> str:
        res = f'{self.ip}/api/{endpoint}'

        if params:
            param_str = '&'.join(f'{k}={v}' for k, v in params.items())
            res = f'{res}?{param_str}'

        return res

    async def _request(self, method, endpoint, json=None, *, _headers: Optional[Dict[str, str]] = None, **params):
        req_kwargs = json_obj.from_not_none(json=json, headers=_headers)
        f = partial(requests.request, method, self._endpoint(endpoint, **params), **req_kwargs)
        log.info(f'{method}: {self._endpoint(endpoint, **params)}')
        return await asyncio.get_running_loop().run_in_executor(self._pool, f)

    async def _get(self, endpoint, *, _headers=None, **params):
        return await self._request('GET', endpoint, **params, _headers=_headers)

    async def _get_j(self, endpoint, *, _headers=None, **params) -> JSONObjOrObjs:
        return json_obj((await self._get(endpoint, **params, _headers=_headers)).json()['result'])

    async def _post(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        return await self._request('POST', endpoint, **params, json=json, _headers=_headers)

    async def _delete(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        return await self._request('DELETE', endpoint, **params, json=json, _headers=_headers)

    async def dump_debug_info(self):
        cur_date = arrow.now().format('YYYYMMDD')
        path = f'/tmp/{cur_date}.cushner.'
        t = await self.system.device_info
        di = path + 'device_info'
        with open(di, 'w') as f:
            f.write(t.pretty)

        t = await self.system.get_logs(arrow.utcnow().shift(hours=-7))
        l = path + 'log'
        with open(l, 'w') as f:
            f.write(t)

        z = path + 'misty.zip'
        with suppress(FileNotFoundError):
            os.remove(z)
        os.system(f'zip {z} {di} {l}')
        print('created', z)

    def __eq__(self, other):
        return self.ip == other.ip

    def __hash__(self):
        return hash(self.ip)


def _run_example():
    """
    example function showing how misty can be used

    in addition, async funcs can be awaited directly from the jupyter console
    """

    async def run():
        api = MistyAPI()

        # run a single task and wait for it to be triggered
        post_res = await api.movement.drive(0, -20, 10000)

        # dispatch multiple tasks at once
        coros = (api.images.take_picture(),
                 api.system.help(),
                 api.system.battery_info  # note: `battery_info` is an "async" property
                 )
        results_in_order = await asyncio.gather(*coros)
        return results_in_order

    asyncio.run(run())


def _create_api_doc():
    """create part of MistyAPI docstring from code"""

    def _fmt_cls_doc(cls):
        d = '\n\t'.join(textwrap.dedent((cls.__doc__ or '')).strip().split('\n'))
        return f'{cls.__name__}: \n\t{d}\n\n'

    res = '\n'.join(map(_fmt_cls_doc, PartialAPI._registered_classes))
    return '\t' + '\n\t'.join(res.splitlines())


MistyAPI.__doc__ = MistyAPI.__doc__.format(partial_api_section=_create_api_doc(),
                                           usage_section='\n    '.join(inspect.getsource(_run_example).splitlines()))
help(MistyAPI)


def __main():
    return


if __name__ == '__main__':
    __main()
