import asyncio
from typing import Set, Optional

from misty_py.apis.base import PartialAPI, print_pretty
from misty_py.misty_ws import EventCallback
from misty_py.subscriptions import SubPayload, FTMsgs, SubType
from misty_py.utils import init_log

__author__ = 'acushner'
log = init_log(__name__)


class FaceAPI(PartialAPI):
    """perform face detection, training, recognition; delete faces"""

    async def list(self, pretty=False) -> Set[str]:
        res = self.saved_faces = set(await self._get_j('faces'))
        if pretty:
            print_pretty(res)
        return res

    async def delete(self, *, name: Optional[str] = None, delete_all: bool = False):
        """rm face[s] from misty"""
        if bool(delete_all) + bool(name) != 1:
            raise ValueError('set exactly one of `name` or `delete_all`')

        await self._delete('faces', **(dict(FaceId=name) if name else {}))

    async def start_detection(self):
        """
        start finding/detecting faces in misty's line of vision
        """
        await self._post('faces/detection/start')

    async def stop_detection(self):
        """stop finding/detecting faces in misty's line of vision"""
        await self._post('faces/detection/stop')

    async def start_training(self, face_id: str):
        """
        start training a particular face
        """
        return await self._post('faces/training/start', dict(FaceId=face_id))

    async def stop_training(self):
        """stop training a particular face"""
        return await self._post('faces/training/stop')

    async def wait_for_training(self, face_id: str):
        """blocking call to wait for face training"""

        async def _wait(sp: SubPayload):
            m = sp.data.message.message
            log.info(m)
            return m == FTMsgs.complete.value

        ecb = EventCallback(_wait)
        async with self.api.ws.sub_unsub(SubType.face_training, ecb):
            await asyncio.gather(
                self.start_training(face_id),
                ecb
            )

    async def cancel_training(self):
        """shouldn't need to call unless you want to manually stop something in progress"""
        return await self._post('faces/training/cancel')

    async def start_recognition(self):
        """start attempting to recognize faces"""
        return await self._post('faces/recognition/start')

    async def stop_recognition(self):
        """stop attempting to recognize faces"""
        return await self._post('faces/recognition/stop')

    async def stop_all(self):
        return await asyncio.gather(self.stop_training(), self.cancel_training(), self.stop_recognition())


def __main():
    pass


if __name__ == '__main__':
    __main()
