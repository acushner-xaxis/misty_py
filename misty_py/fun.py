import random

from misty_py.api import MistyAPI
from misty_py.utils import MISTY_URL

__author__ = 'acushner'

api = MistyAPI(MISTY_URL)


async def random_simpsons_quote():
    await api.audio.play(f'simpsons_{random.choice(range(1, 101))}.mp3')
