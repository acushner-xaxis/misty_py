from base64 import b64decode
from typing import Optional

from misty_py.utils import RestAPI, JSONObjOrObjs, json_obj

__author__ = 'acushner'


# noinspection PyProtectedMember
class PartialAPI(RestAPI):
    """
    represent part of the overall api

    separate out methods into logical groups such as face, image, audio, etc
    """
    _registered_classes = set()  # only used for MistyAPI's __doc__

    def __init__(self, api):
        from misty_py.api import MistyAPI
        self.api: MistyAPI = api

    def __init_subclass__(cls, **kwargs):
        if not cls.__name__.startswith('_'):
            cls._registered_classes.add(cls)

    async def _get(self, endpoint, *, _headers=None, **params):
        return await self.api._get(endpoint, _headers=_headers, **params)

    async def _get_j(self, endpoint, *, _headers=None, **params) -> JSONObjOrObjs:
        return await self.api._get_j(endpoint, _headers=_headers, **params)

    async def _post(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        return await self.api._post(endpoint, json, _headers=_headers, **params)

    async def _delete(self, endpoint, json: Optional[dict] = None, *, _headers=None, **params):
        return await self.api._delete(endpoint, json, _headers=_headers, **params)


def __main():
    pass


if __name__ == '__main__':
    __main()
WIDTH = 480
HEIGHT = 272
AUDIO_SIZE_LIMIT = 3 * 2 ** 20  # 3 mb


def print_pretty(o):
    print('\n'.join(map(str, o)))


def write_outfile(outfile, content, as_base64):
    if outfile:
        if as_base64:
            content = b64decode(json_obj.from_str(content).result.base64)
        with open(outfile, 'wb') as f:
            f.write(content)