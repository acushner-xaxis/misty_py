import asyncio
from functools import wraps
from io import BytesIO
from typing import Dict, Optional, Coroutine

from misty_py.apis.base import PartialAPI, write_outfile, print_pretty, AUDIO_SIZE_LIMIT
from misty_py.misty_ws import EventCallback
from misty_py.subscriptions import SubPayload, SubType, HandlerType
from misty_py.utils import json_obj, generate_upload_payload, wait_in_order, delay, wait_first

__author__ = 'acushner'


class AudioAPI(PartialAPI):
    """record, play, change volume, manage audio files"""

    async def get(self, file_name: str, outfile='', *, as_base64=False) -> BytesIO:
        res = await self._get('audio', FileName=file_name, Base64=as_base64)
        write_outfile(outfile, res.content, as_base64)
        return BytesIO(res.content)

    async def list(self, pretty=False) -> Dict[str, json_obj]:
        """
        get audio metadata available on device as dict(name=json)
        store in `self.saved_audio`
        return dict
        """
        audio = await self._get_j('audio/list')
        res = self.saved_audio = json_obj((a.name, a) for a in audio)
        if pretty:
            print_pretty(res)
        return res

    async def upload(self, file_path: str, *, prefix: str = '', apply_immediately: bool = False,
                     overwrite_existing: bool = True, data: Optional[bytes] = None):
        """
        NOTE: prefix is busted for now and will not be used. waiting on fix from misty robotics

        upload data (mp3, wav, not sure what else) to misty

        for some reason it's faster to upload and play separately
        rather than set `apply_immediately` on the upload request

        file_path is the local path to the file
        prefix, if provided, will be prepended to the name as placed on misty
        """
        payload = generate_upload_payload(prefix, file_path, False, overwrite_existing, limit=AUDIO_SIZE_LIMIT,
                                          data=data)
        res = await self._post('audio', payload)
        if apply_immediately:
            await self.play(payload.FileName)
        return res

    async def play(self, name: str, volume: int = 100, *, how_long_secs: Optional[int] = None, blocking=False,
                   on_done: Optional[Coroutine] = None):
        """
        play audio for how long you want to

        use `how_long_secs` to interrupt audio after a certain amount of time has elapsed
        use `blocking` to indicate that this call should not complete until audio is done playing
        use `on_done` as a callback to indicate what should be done when audio is complete
        """
        payload = dict(FileName=name, Volume=min(max(volume, 1), 100))
        res = await self._post('audio/play', payload)
        if res.ok:
            await self._handle_blocking_play_call(name, how_long_secs, blocking, on_done)
        return res

    async def _handle_blocking_play_call(self, name: str, how_long_secs: float, blocking: bool,
                                         on_done: Optional[Coroutine]):
        """
        handle waiting for audio to finish. we need to either:

        - block until the song completes
        - block until either the song completes or the elapsed time has expired
        - optionally await a callback (`on_done`)

        or:
        - do nothing
        """

        try:
            force_stop = completed = None
            if on_done or blocking:
                completed = wait_in_order(self._handle_audio_complete(name))

            if how_long_secs:
                force_stop = delay(how_long_secs, self.stop_playing())

            if blocking or on_done or how_long_secs:
                t = asyncio.create_task(wait_in_order(wait_first(force_stop, completed), on_done))
                if blocking:
                    return await t
                return t
        except asyncio.CancelledError:
            await self.stop_playing()
            raise

    async def _handle_audio_complete(self, name):
        """subscribe and wait for an audio complete event"""

        async def _wait_one(sp: SubPayload):
            return sp.data.message.metaData.name == name

        event = EventCallback(_wait_one)
        try:
            async with self.api.ws.sub_unsub(SubType.audio_play_complete, event):
                await event
        except asyncio.CancelledError:
            event.set()
            raise

    async def stop_playing(self):
        """trigger a small amount of silence to stop a playing song"""
        return await self.play('silence_stop.mp3')

    async def delete(self, file_name: str):
        return await self._delete('audio', dict(FileName=file_name))

    async def set_default_volume(self, volume):
        return await self._post('audio/volume', dict(Volume=min(max(volume, 0), 100)))

    async def _handle_blocking_record_call(self, how_long_secs, blocking):
        if blocking and not how_long_secs:
            raise ValueError('if you want to block, must provide both `how_long_secs`')

        if how_long_secs is not None:
            how_long_secs = min(max(how_long_secs, 0), 60)
            coro = delay(how_long_secs, self.stop_recording())
            if blocking:
                await coro
            else:
                asyncio.create_task(coro)

    async def record(self, filename: str, how_long_secs: Optional[float] = None, blocking=False):
        """record audio"""
        fn = f'{filename.rstrip(".wav")}.wav'
        res = await self._post('audio/record/start', json_obj(FileName=fn))
        await self._handle_blocking_record_call(how_long_secs, blocking)
        return res

    async def stop_recording(self):
        """stop recording audio"""
        await self._post('audio/record/stop')

    async def start_key_phrase_recognition(self, on_recognition: HandlerType):
        @wraps(on_recognition)
        async def _wrapper(sp: SubPayload):
            asyncio.create_task(sp.sub_id.unsubscribe())
            return await on_recognition(sp)

        await self.api.ws.subscribe(SubType.key_phrase_recognized, _wrapper)
        await self._post('audio/keyphrase/start')

    async def wait_for_key_phrase(self):
        async def _wait_one(_: SubPayload):
            return True

        ecb = EventCallback(_wait_one)
        await self.start_key_phrase_recognition(ecb)
        await ecb

    async def stop_key_phrase_recognition(self):
        await self._post('audio/keyphrase/stop')
        await self.api.ws.unsubscribe(SubType.key_phrase_recognized)


def __main():
    pass


if __name__ == '__main__':
    __main()
