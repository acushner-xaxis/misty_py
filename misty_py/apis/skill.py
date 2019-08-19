from typing import Optional, Dict

from misty_py.apis.base import PartialAPI
from misty_py.utils import json_obj

__author__ = 'acushner'


class SkillAPI(PartialAPI):
    """interact with on-robot skills available on misty"""

    async def stop(self, skill_name: Optional[str] = None):
        await self._post('skills/cancel', json_obj.from_not_none(Skill=skill_name))

    async def delete(self, skill_uid: str):
        await self._delete('skills', Skill=skill_uid)

    async def get_running(self):
        return await self._get_j('skills/running')

    async def get(self):
        return await self._get_j('skills')

    async def run(self, skill_name_or_uid, method: Optional[str] = None):
        return (await self._post('skills/start',
                                 json_obj.from_not_none(Skill=skill_name_or_uid, Method=method))).json()['result']

    async def save(self, zip_file_name: str, *, apply_immediately: bool = False, overwrite_existing: bool = True):
        await self._post('skills', dict(File=zip_file_name, ImmediatelyApply=apply_immediately,
                                        OverwriteExisting=overwrite_existing))

    async def trigger_skill_event(self, skill_uid: str, event_name: str, json: Optional[Dict] = None):
        """send an event to a currently running skill"""
        payload = json_obj.from_not_none(UniqueId=skill_uid, EventName=event_name, Payload=json)
        await self._post('skills/event', payload)


def __main():
    pass


if __name__ == '__main__':
    __main()
