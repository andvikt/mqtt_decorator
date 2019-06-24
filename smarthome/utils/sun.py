from datetime import datetime, timedelta
from functools import partial
from typing import Callable, Optional, Generic
from ..const import _T, _X

import attr
from astral import Astral

from .utils import TimeTracker, CustomTime
from functools import wraps
from asyncio_primitives import utils as autils
import asyncio


@attr.s
class Sun:

    city_name: str = attr.ib()

    def __attrs_post_init__(self):
        self.loc = Astral().geocoder[self.city_name]

    def get_time(self, name, date=None, offset:timedelta = timedelta(seconds=0))->TimeTracker:
        date = date or CustomTime.now().date()
        next_time = self.loc.sun(date)[name] + offset
        while next_time <= CustomTime.now():
            date = date + timedelta(days=1) + offset
            next_time = self.loc.sun(date)[name]
        return TimeTracker(next_time)

    def rule(self, name, offset:timedelta = timedelta(seconds=0)):
        assert name in ['sunrise', 'dusk', 'sunset', 'dawn']
        def deco(foo):
            @wraps(foo)
            async def wrapper(*args, **kwargs) -> asyncio.Task:
                @autils.endless_loop
                async def _loop():
                    await self.get_time(name, offset=offset).wait()
                    await autils.async_run(foo, *args, **kwargs)
                return await _loop()
            return wrapper
        return deco

    def rule_sunrise(self, offset = timedelta(seconds=0)):
        return self.rule('sunrise', offset=offset)

    def rule_dusk(self, offset = timedelta(seconds=0)):
        return self.rule('dusk', offset=offset)

    def rule_sunset(self, offset = timedelta(seconds=0)):
        return self.rule('sunset', offset=offset)

    def rule_dawn(self, offset = timedelta(seconds=0)):
        return self.rule('dawn', offset=offset)
