from abc import ABC, abstractmethod
from io import BytesIO

from misty_py.apis.base import PartialAPI
from misty_py.misty_ws import EventCallback
from misty_py.subscriptions import SubPayload, SubType
from misty_py.utils import Coords

__author__ = 'acushner'


class _SlamHelper(PartialAPI, ABC):
    """
    context manager to handle initializing and stopping slam functionality

    used by the NavigationAPI
    """

    def __init__(self, api, endpoint: str, timeout_secs=15.0):
        super().__init__(api)
        self._endpoint = endpoint
        self._num_current_slam_streams = 0
        self._ready_cb = EventCallback(self._sensor_ready, timeout_secs)

    @abstractmethod
    async def _sensor_ready(self, sp: SubPayload):
        """handler func that indicates when the sensor is ready"""

    async def start(self):
        self._ready_cb.clear()
        await self._post(f'slam/{self._endpoint}/start')

    async def stop(self):
        return await self._post(f'slam/{self._endpoint}/stop')

    async def reset(self):
        return await self._post('slam/reset')

    async def __aenter__(self):
        self._num_current_slam_streams += 1
        if self._num_current_slam_streams == 1:
            await self.start()
            async with self.api.ws.sub_unsub(SubType.self_state, self._ready_cb):
                await self._ready_cb

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._num_current_slam_streams -= 1
        if self._num_current_slam_streams == 0:
            await self.stop()


class _SlamMapping(_SlamHelper):
    def __init__(self, api):
        super().__init__(api, 'map')

    async def _sensor_ready(self, sp: SubPayload):
        ss = sp.data.message.slamStatus
        return (ss.runMode == 'Exploring'
                and all(v in ss.statusList for v in 'Ready Exploring HasPose Streaming'.split()))


class _SlamStreaming(_SlamHelper):
    def __init__(self, api):
        super().__init__(api, 'streaming')

    async def _sensor_ready(self, sp: SubPayload):
        ss = sp.data.message.slamStatus
        return all(v in ss.statusList for v in 'Ready Streaming'.split())


class _SlamTracking(_SlamHelper):
    def __init__(self, api):
        super().__init__(api, 'track')

    async def _sensor_ready(self, sp: SubPayload):
        ss = sp.data.message.slamStatus
        return (ss.runMode == 'Tracking'
                and all(v in ss.statusList for v in ('Ready', 'Tracking', 'HasPose', 'Streaming')))


class NavigationAPI(PartialAPI):
    """
    control mapping, tracking, driving, etc

    can also take depth/fisheye pics
    """

    def __init__(self, api):
        super().__init__(api)
        self.slam_streaming = _SlamStreaming(api)
        self.slam_mapping = _SlamMapping(api)
        self.slam_tracking = _SlamTracking(api)

    async def reset_slam(self):
        return await self._post('slam/reset')

    async def take_depth_pic(self):
        async with self.slam_streaming:
            return await self._get_j('cameras/depth')

    async def take_fisheye_pic(self) -> BytesIO:
        async with self.slam_streaming:
            res = await self._get('cameras/fisheye')
            return BytesIO(res.content)

    async def get_map(self):
        return await self._get_j('slam/map')

    async def map(self):
        """# algo for misty to move around slowly mapping her environment"""
        # TODO: implement
        raise NotImplementedError

    async def drive_to_coordinates(self, coords: Coords):
        async with self.slam_tracking:
            await self._post('drive/coordinates', dict(Destination=Coords.format(coords)))

    async def follow_path(self, *coords: Coords):
        async with self.slam_tracking:
            if len(coords) == 1:
                return await self.drive_to_coordinates(*coords)
            return await self._post('drive/path', dict(Path=Coords.format(*coords)))


def __main():
    pass


if __name__ == '__main__':
    __main()
