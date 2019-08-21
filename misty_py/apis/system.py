from typing import NamedTuple, Dict, Optional

import arrow

from misty_py.apis.base import PartialAPI
from misty_py.utils import json_obj

__author__ = 'acushner'


class BatteryInfo(NamedTuple):
    percent: float
    metadata: json_obj

    @classmethod
    def from_meta(cls, data):
        cp = data.chargePercent
        if cp:
            cp *= 100
        return cls(cp, data)


class SystemAPI(PartialAPI):
    """
    interact with various system elements on the robot

    get logs, battery, etc
    """

    async def clear_display_text(self):
        return await self._post('text/clear')

    async def get_wifi_networks(self) -> Dict[str, str]:
        networks = await self._get_j('networks')
        return {n.ssid: n for n in networks}

    async def connect_wifi(self, ssid):
        """connect to known wifi"""
        return await self._post('networks', json_obj(NetworkId=ssid))

    async def set_wifi_network(self, name, password):
        """set up with username and password"""
        payload = dict(NetworkName=name, Password=password)
        return await self._post('network', payload)

    async def forget_wifi(self, ssid):
        return await self._delete('networks', json_obj(NetworkId=ssid))

    async def scan_wifi(self):
        """find available wifi networks"""
        return await self._get_j('networks/scan')

    @property
    async def battery_info(self) -> BatteryInfo:
        return BatteryInfo.from_meta(await self._get_j('battery'))

    @property
    async def device_info(self):
        return await self._get_j('device')

    async def help(self, endpoint: Optional[str] = None):
        """specs for the system at large"""
        return await self._get_j('help', **json_obj.from_not_none(command=endpoint))

    async def get_logs(self, date: arrow.Arrow = arrow.now()) -> str:
        params = json_obj()
        if date:
            params.date = date.format('YYYY/MM/DD')
        return (await self._get('logs', **params)).json()['result']

    @property
    async def log_level(self) -> str:
        return (await self._get('logs/level')).json()['result']

    async def set_log_level(self, log_level: str):
        return await self._post('logs/level', json_obj(LogLevel=log_level))

    @property
    async def is_update_available(self) -> bool:
        return (await self._get('system/updates')).json()['result']

    async def perform_system_update(self):
        return await self._post('system/update')

    async def get_websocket_names(self, class_name: Optional[str] = None):
        """specs for websocket api"""
        params = json_obj()
        if class_name:
            params.websocketClass = class_name
        return await self._get_j('websockets', **params)

    @property
    async def websocket_version(self):
        return (await self._get('websocket/version')).json()['result']

    async def send_to_backpack(self, msg: str):
        """not sure what kind of data/msg we can send - perhaps Base64 encode to send binary data?"""
        return await self._post('serial', dict(Message=msg))

    async def set_flashlight(self, on: bool = True):
        return await self._post('flashlight', dict(On=on))

    async def reboot(self, core=True, sensory_services=True):
        return await self._post('reboot', json_obj(Core=core, SensoryServices=sensory_services))


def __main():
    pass


if __name__ == '__main__':
    __main()
