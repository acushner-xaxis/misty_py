import asyncio
from contextlib import suppress
from typing import NamedTuple, Optional, Dict

import arrow

from misty_py.api import MistyAPI, MISTY_URL
from misty_py.subscriptions import SubData, HandlerType, SubType, Actuator, SubEC, EventCallback

__author__ = 'acushner'

api = MistyAPI(MISTY_URL)

questions_comments = '''
- documentation on how the websockets API actually acts is pretty fragmented
- sometimes, even though face recog is running, it just won't recognize faces. i have no idea why
    - i think it was an ephemeral issue with onboard sensors failing
    - rebooting helped
- how can i tell, easily, when face training is done?
'''


class Person(NamedTuple):
    name: str
    target_acquired_phrase: str
    theme_song: str

    async def on_find(self, api: MistyAPI):
        await api.movement.halt()
        eh = EventCallback(wait_one)
        print('first', arrow.utcnow())
        async with api.ws.sub_unsub(SubType.audio_play_complete, eh):
            await api.audio.play(self.target_acquired_phrase)
            await eh.wait()
        print('first done', arrow.utcnow())

        print('second', arrow.utcnow())
        await api.audio.play(self.theme_song, how_long_secs=6, blocking=True)
        print('second done', arrow.utcnow())


people: Dict[str, Person] = {}


def add_person(person: Person):
    people[person.name] = person


add_person(Person('sweettuse', 'sweettuse_recognized.mp3', 'price_is_right.mp3'))


# ======================================================================================================================


async def wait_one(sd: SubData):
    print('wait_one', sd)
    return True


class UnchangedValue:
    """useful for determining when something is done, say, moving"""

    def __init__(self):
        self._prev: Optional[SubData] = None
        self._ready = asyncio.Event()

    __call__: HandlerType

    async def __call__(self, sd: SubData):
        print('uv', sd)
        if self._prev is None:
            self._prev = sd
            return
        prev, self._prev = self._prev, sd
        with suppress(AttributeError):
            if prev.data.message.value == sd.data.message.value:
                self._ready.set()

    async def wait(self):
        await self._ready.wait()


async def _handle_head_movement(yaw):
    uv = UnchangedValue()
    sub_ec = SubEC.from_sub_ec(SubType.actuator_position, Actuator.yaw.event_condition)
    await api.movement.move_head(yaw=yaw)
    async with api.ws.sub_unsub(sub_ec, uv, 400):
        await uv.wait()


async def _handle_face_recognition(sd: SubData):
    print('face_rec', sd)
    person = people.pop(sd.data.message.personName, None)
    if person:
        print('found', person)
        await sd.sub_req.unsubscribe()
        await person.on_find(api)
        return True


async def _init_face_recognition() -> EventCallback:
    print('starting face recognition')
    await api.faces.start_recognition()
    eh = EventCallback(_handle_face_recognition)
    await api.ws.subscribe(SubType.face_recognition, eh)
    return eh


async def run():
    print('started')
    await asyncio.sleep(3)
    face_handler = await _init_face_recognition()
    await _handle_head_movement(200)
    await face_handler.wait()
    await api.faces.stop_recognition()
    print('done')


def __main():
    asyncio.run(run())
    print('we did something')
    # asyncio.run(asyncio.gather(*asyncio.Task.all_tasks()))
    pass


if __name__ == '__main__':
    __main()
