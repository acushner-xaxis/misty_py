import asyncio
from contextlib import suppress
from typing import Optional, Dict, NamedTuple

from misty_py.apis.base import PartialAPI
from misty_py.misty_ws import EventCallback
from misty_py.subscriptions import Actuator, Sub, SubPayload, SubType
from misty_py.utils import json_obj, ArmSettings, HeadSettings, first

__author__ = 'acushner'


class MovementAPI(PartialAPI):
    """specifically control head, arms, driving movement, etc"""

    @staticmethod
    def _validate_vel_pct(**vel_pcts):
        fails = {name: val for name, val in vel_pcts.items()
                 if val is not None
                 and not -100 <= val <= 100}
        if fails:
            raise ValueError(f'invalid value for vel_pct: {fails}, must be in range [-100, 100] or `None`')

    async def drive(self, linear_vel_pct: int = 0, angular_vel_pct: int = 0, time_ms: Optional[int] = None):
        """
        angular_vel_pct: -100 is full speed counter-clockwise, 100 is full speed clockwise
        """
        angular_vel_pct *= -1
        self._validate_vel_pct(linear_vel_pct=linear_vel_pct, angular_vel_pct=angular_vel_pct)
        payload = json_obj.from_not_none(LinearVelocity=linear_vel_pct, AngularVelocity=angular_vel_pct)
        endpoint = 'drive'

        if time_ms:
            payload['TimeMS'] = time_ms
            endpoint += '/time'

        return await self._post(endpoint, payload)

    async def drive_track(self, left_track_vel_pct: int = 0, right_track_vel_pct: int = 0):
        """control drive tracks individually"""
        self._validate_vel_pct(left_track_vel_pct=left_track_vel_pct, right_track_vel_pct=right_track_vel_pct)
        return await self._post('drive/track',
                                dict(LeftTrackSpeed=left_track_vel_pct, RightTrackSpeed=right_track_vel_pct))

    async def move_arms(self, l_position: Optional[float] = None, l_velocity: Optional[float] = None,
                        r_position: Optional[float] = None, r_velocity: Optional[float] = None):
        """pass either/both left and right arm settings"""
        arm_settings = (ArmSettings('left', l_position, l_velocity),
                        ArmSettings('right', r_position, r_velocity))
        payload = {k: v for arm in arm_settings for k, v in arm.json.items()}
        if payload:
            return await self._post('arms/set', payload)

    async def move_head(self, pitch: Optional[float] = None, roll: Optional[float] = None, yaw: Optional[float] = None,
                        velocity: Optional[float] = None):
        """
        all vals in range [-100, 100]

        pitch: up and down
        roll: tilt (ear to shoulder)
        yaw: turn left and right
        velocity: how quickly
        """
        return await self._post('head', HeadSettings(pitch, roll, yaw, velocity).json)

    async def stop(self, *, everything=False):
        """
        stop motion

        if `everything` is set, will stop everything (i.e. halt)
        """
        if everything:
            return await self.halt()
        return await self._post('drive/stop')

    async def halt(self):
        """stop everything"""
        return await self._post('halt')

    async def drive_arc(self, heading_degrees: float, radius_m: float, time_ms: float, *, reverse: bool = False):
        payload = json_obj(Heading=heading_degrees * -1, Radius=radius_m, TimeMs=time_ms, Reverse=reverse)
        return await self._post('drive/arc', payload)

    async def get_actuator_positions(self, normalize=True) -> Dict[Actuator, float]:
        """
        get actuator positions from misty and, if set, normalize to values between
        -100 and 100 based on calibrations
        """
        res: Dict[Sub, float] = {}
        submitted = False

        async def _wait_one(sp: SubPayload):
            nonlocal expected_sub_ids
            if not submitted:
                return False
            expected_sub_ids -= {sp.sub_id}
            with suppress(Exception):
                res[sp.sub_id.sub] = sp.data.message.value
            await sp.sub_id.unsubscribe()
            return not expected_sub_ids

        ecb = EventCallback(_wait_one)

        expected_sub_ids = set(await self.api.ws.subscribe(SubType.actuator_position, ecb))
        submitted = True
        await ecb

        res = {Actuator(first(sub.ec).value): v for sub, v in res.items()}
        if not normalize:
            return res
        calibrations = _get_calibrated_actuator_positions()
        return {k: calibrations[k].normalize(v) for k, v in res.items()}


class PosZeroNeg(NamedTuple):
    pos: float  # misty value when setting to 100 via the api
    zero: float  # misty value when setting to 0 via the api
    neg: float  # misty value when setting to -100 via the api

    def normalize(self, val):
        if val < self.zero and self.pos < self.zero:
            return abs(self._normalize(self.pos, val))
        return -abs(self._normalize(self.neg, val))

    def _normalize(self, end, val):
        return (val - self.zero) / (end - self.zero)


async def calibrate_misty():
    """
    move misty's actuators to extreme positions and record the values
    """
    from misty_py.api import MistyAPI
    api = MistyAPI()
    res = {}
    await api.movement.move_head(0, 0, 0, 50)
    await api.movement.move_arms(-50, -50, 50, 50)
    await asyncio.sleep(2)

    async def _head(*_args, **_kwargs):
        await api.movement.move_head(*_args, **_kwargs)
        await asyncio.sleep(3)
        return (await api.movement.get_actuator_positions(normalize=False))[a]

    for a in Actuator.pitch, Actuator.roll, Actuator.yaw:
        kwargs = {a.name: 110, 'velocity': 60}
        pos = await _head(**kwargs)

        kwargs = {a.name: -110, 'velocity': 60}
        neg = await _head(**kwargs)

        zero = await _head(0, 0, 0, 50)
        res[a] = PosZeroNeg(pos, zero, neg)

    async def _arms(**_kwargs):
        await api.movement.move_arms(**_kwargs)
        await asyncio.sleep(2)
        positions = await api.movement.get_actuator_positions(normalize=False)
        return positions[Actuator.left_arm], positions[Actuator.right_arm]

    l_pos, r_pos = await _arms(l_position=110, r_position=110, l_velocity=80, r_velocity=80)
    l_neg, r_neg = await _arms(l_position=-110, r_position=-110, l_velocity=80, r_velocity=80)
    l_0, r_0 = await _arms(l_position=0, r_position=0, l_velocity=50, r_velocity=50)

    res[Actuator.left_arm] = PosZeroNeg(l_pos, l_0, l_neg)
    res[Actuator.right_arm] = PosZeroNeg(r_pos, r_0, r_neg)

    print()
    print(json_obj((k.name, v) for k, v in res.items()).pretty)
    return res


# based off calibrating my own version of misty
default_actuator_calibrations = {
    Actuator.pitch: PosZeroNeg(-36, -6, 22),
    Actuator.roll: PosZeroNeg(42, 1, -39),
    Actuator.yaw: PosZeroNeg(-85, -2, 80),
    Actuator.left_arm: PosZeroNeg(-26, 2, 89),
    Actuator.right_arm: PosZeroNeg(-27, -5, 89),
}


def _get_calibrated_actuator_positions() -> Dict[Actuator, PosZeroNeg]:
    try:
        from misty_py.utils.local_conf import actuator_calibrations
    except (ImportError, ModuleNotFoundError):
        import warnings
        warnings.warn('Using default actuator calibrations. run `calibrate_misty` in movement.py '
                      'and store the results in `misty_py.utils.local_conf.py` under `actuator_calibrations` '
                      'for more accurate results')
        return default_actuator_calibrations

    return {Actuator[name]: PosZeroNeg(*vals) for name, vals in actuator_calibrations.items()}


def __main():
    print(asyncio.run(calibrate_misty()))


if __name__ == '__main__':
    __main()
