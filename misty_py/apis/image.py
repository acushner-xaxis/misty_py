import asyncio
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Dict, Optional, NamedTuple, Union

from misty_py.apis.base import PartialAPI, print_pretty, write_outfile
from misty_py.utils import save_data_locally, json_obj, generate_upload_payload, RGB, delay

__author__ = 'acushner'


class BlinkSettings(NamedTuple):
    closed_eye_min_ms: int = None
    closed_eye_max_ms: int = None
    open_eye_min_ms: int = None
    open_eye_max_ms: int = None
    blink_image_map: dict = None

    @classmethod
    def from_json(cls, data):
        return cls(data.closedEyeMinMs, data.closedEyeMaxMs, data.openEyeMinMs, data.openEyeMaxMs, data.blinkImages)

    @property
    def json(self):
        return json_obj.from_not_none(
            closedEyeMinMs=self.closed_eye_min_ms,
            closedEyeMaxMs=self.closed_eye_max_ms,
            openEyeMinMs=self.open_eye_min_ms,
            openEyeMaxMs=self.open_eye_max_ms,
            blinkImages=self.blink_image_map
        )


class ImageAPI(PartialAPI):
    """handle pics, video, uploading/downloading images, changing led color, etc"""

    @staticmethod
    def save_image_locally(path, data: BytesIO):
        save_data_locally(path, data, '.jpg')

    @staticmethod
    def save_video_locally(path, data: BytesIO):
        save_data_locally(path, data, '.mov')

    async def list(self, pretty=False) -> Dict[str, json_obj]:
        """
        get images available on device as dict(name=json)
        store in `self.saved_images`
        return dict
        """
        images = await self._get_j('images/list')
        res = self.saved_images = json_obj((i.name, i) for i in images)
        if pretty:
            print_pretty(res)
        return res

    async def get(self, file_name: str, outfile='', as_base64=False) -> BytesIO:
        """
        get binary data image data from misty
        """
        res = await self._get('images', FileName=file_name, Base64=as_base64)
        write_outfile(outfile, res.content, as_base64)
        return BytesIO(res.content)

    async def upload(self, file_name: str, *, prefix: str = '', width: Optional[int] = None,
                     height: Optional[int] = None, apply_immediately: bool = False,
                     overwrite_existing: bool = True):
        """
        NOTE: prefix is busted for now and will not be used. waiting on fix from misty robotics

        upload a local image to misty

        file_name is the name of the file locally
        prefix, if provided, will be prepended to the name as placed on misty
        """
        payload = generate_upload_payload(prefix, file_name, apply_immediately, overwrite_existing)
        payload.add_if_not_none(Width=width, Height=height)
        return await self._post('images', payload)

    async def display(self, file_name: str, time_out_secs: Optional[float] = None, alpha: float = 1.0):
        """
        file_name: name on device
        time_out_secs: no idea what this does. seems to have no effect
        alpha: should be between 0 (totally transparent) and 1 (totally opaque), inclusive
        """
        return await self._post('images/display', dict(FileName=file_name, TimeOutSeconds=time_out_secs, Alpha=alpha))

    async def set_led(self, rgb: RGB = RGB(0, 0, 0)):
        """
        change color of torso's led

        default to turning led off
        """
        rgb.validate()
        return await self._post('led', rgb.json)

    async def delete(self, file_name: str):
        return await self._delete('images', dict(FileName=file_name))

    @staticmethod
    def _validate_take_picture(file_name, width, height, show_on_screen):
        if bool(width) + bool(height) == 1:
            raise ValueError("must supply either both width and height, or neither. can't supply just one")

        if show_on_screen and not file_name:
            raise ValueError('in order for `show_on_screen` to work, you must provide a file_name')

    async def take_picture(self, file_name: Optional[str] = None, width: Optional[int] = None,
                           height: Optional[int] = None,
                           *, show_on_screen: Optional[bool] = False,
                           overwrite_existing=True):
        """
        if height is supplied, so must be width, and vice versa
        if you want to display on the screen, you must provide a filename

        # TODO: better way return data? maybe decode the base64 vals and return them?
        """
        self._validate_take_picture(file_name, width, height, show_on_screen)

        payload = json_obj.from_not_none(Base64=True, FileName=file_name, Width=width, Height=height,
                                         DisplayOnScreen=show_on_screen, OverwriteExisting=overwrite_existing)
        return await self._get_j('cameras/rgb', **payload)

    async def start_recording_video(self, how_long_secs: Optional[int] = None):
        """
        video is limited:
        - record up to 10 seconds
        - can only store one recording at a time
        """
        res = await self._post('video/record/start')
        if how_long_secs:
            how_long_secs = min(max(1, how_long_secs), 10)
            asyncio.create_task(delay(how_long_secs, self.stop_recording_video()))
        return res

    async def stop_recording_video(self):
        return await self._post('video/record/stop')

    async def get_recorded_video(self) -> BytesIO:
        res = await self._get('video')
        return BytesIO(res.content)

    async def get_blink_settings(self) -> BlinkSettings:
        return BlinkSettings.from_json(await self._get_j('blink/settings'))

    async def set_blinking(self, on=True):
        return await self._post('blink', json_obj(Blink=on))

    async def set_blink_settings(self, settings: Union[BlinkSettings, json_obj]):
        if isinstance(settings, BlinkSettings):
            settings = settings.json
        return await self._post('blink/settings', settings)

    async def remove_blink_mappings(self, image: str, *images: str):
        return await self._delete('blink/images', json_obj(BlinkImages=(image,) + images))

    @asynccontextmanager
    async def patch_blink_settings(self, settings: BlinkSettings):
        """temporarily set blink settings to something different and then reset to original"""
        orig = await self.get_blink_settings()
        try:
            await self.set_blink_settings(settings)
            yield
        finally:
            await self.set_blink_settings(orig)


default_eye_params = {
    "closedEyeMaxMs": 200,
    "closedEyeMinMs": 100,
    "openEyeMaxMs": 8000,
    "openEyeMinMs": 1000
}

default_eye_params_full = {
    "blinkImages": {
        "e_Amazement.jpg": "e_SystemBlinkLarge.jpg",
        "e_Anger.jpg": "e_SystemBlinkStandard.jpg",
        "e_ApprehensionConcerned.jpg": "e_SystemBlinkStandard.jpg",
        "e_ContentLeft.jpg": "e_SystemBlinkStandard.jpg",
        "e_ContentRight.jpg": "e_SystemBlinkStandard.jpg",
        "e_DefaultContent.jpg": "e_SystemBlinkStandard.jpg",
        "e_Disoriented.jpg": "e_SystemBlinkStandard.jpg",
        "e_EcstacyStarryEyed.jpg": "e_SystemBlinkLarge.jpg",
        "e_Fear.jpg": "e_SystemBlinkStandard.jpg",
        "e_Joy.jpg": "e_SystemBlinkStandard.jpg",
        "e_Joy2.jpg": "e_SystemBlinkStandard.jpg",
        "e_JoyGoofy2.jpg": "e_SystemBlinkLarge.jpg",
        "e_Love.jpg": "e_SystemBlinkStandard.jpg",
        "e_Rage.jpg": "e_SystemBlinkLarge.jpg",
        "e_Rage3.jpg": "e_SystemBlinkLarge.jpg",
        "e_Rage4.jpg": "e_SystemBlinkLarge.jpg",
        "e_Sadness.jpg": "e_SystemBlinkStandard.jpg",
        "e_Sleepy.jpg": "e_SystemBlinkStandard.jpg",
        "e_Sleepy2.jpg": "e_SystemBlinkStandard.jpg",
        "e_Sleepy3.jpg": "e_SystemBlinkStandard.jpg",
        "e_Sleepy4.jpg": "e_SystemBlinkStandard.jpg",
        "e_Surprise.jpg": "e_SystemBlinkLarge.jpg",
        "e_SystemCamera.jpg": "e_SystemBlinkStandard.jpg",
        "e_Terror.jpg": "e_SystemBlinkLarge.jpg",
        "e_Terror2.jpg": "e_SystemBlinkLarge.jpg",
        "e_TerrorLeft.jpg": "e_SystemBlinkLarge.jpg",
        "e_TerrorRight.jpg": "e_SystemBlinkLarge.jpg"
    },
    "closedEyeMaxMs": 200,
    "closedEyeMinMs": 100,
    "openEyeMaxMs": 8000,
    "openEyeMinMs": 1000
}


def __main():
    pass


if __name__ == '__main__':
    __main()
