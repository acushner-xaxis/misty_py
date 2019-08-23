from __future__ import annotations

from typing import NamedTuple

import sty as sty


class RGB(NamedTuple):
    r: int
    g: int
    b: int

    @property
    def hex(self) -> str:
        return hex((self.r << 16) + (self.g << 8) + self.b)

    @classmethod
    def from_hex(cls, h) -> RGB:
        nums = []
        for _ in range(3):
            nums.append(h & 0xff)
            h >>= 8
        return cls(*reversed(nums))

    @property
    def json(self):
        return dict(red=self.r, green=self.g, blue=self.b)

    def color_str(self, s, set_bg=False) -> str:
        """
        create str with different foreground(default)/background color for use in terminal
        reset to default at end of str
        """
        layer = sty.bg if set_bg else sty.fg
        return f'{layer(*self[:3])}{s}{layer.rs}'

    @staticmethod
    def _add_components(v1, v2):
        return int(((v1 ** 2 + v2 ** 2) / 2) ** .5)

    def __add__(self, other) -> 'RGB':
        add = self._add_components
        return RGB(add(self.r, other.r), add(self.g, other.g), add(self.b, other.b))

    def validate(self):
        if any(c < 0 or c > 255 for c in self):
            raise ValueError(f'color values must be in [0, 255]: {self}')


