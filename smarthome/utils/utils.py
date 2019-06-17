import asyncio
from datetime import datetime, timedelta
from typing import Dict, Generator, Tuple

import attr

from ..const import _X, _T


def dict_in(dct: Dict[_X, _T], *_in: _X) -> Generator[Tuple[_X, _T], None, None]:
    for x, y in dct.items():
        if x in _in:
            yield x, y

class CustomTime(datetime):
    pass


@attr.s
class TimeTracker:

    time: CustomTime = attr.ib()

    @classmethod
    def now(cls):
        return cls(CustomTime.now())

    async def wait(self):
        sleep = (self.time - CustomTime.now()).total_seconds()
        if sleep > 0:
            await asyncio.sleep(sleep)

    def __add__(self, other):
        if isinstance(other, (int, float)):
            other = timedelta(minutes=other)
        elif not isinstance(other, timedelta):
            raise TypeError('Can only add int or float as minutes or timedelta')
        return TimeTracker(self.time + other)

    def __sub__(self, other):
        if isinstance(other, (int, float)):
            other = timedelta(minutes=other)
        elif not isinstance(other, timedelta):
            raise TypeError('Can only add int or float as minutes or timedelta')
        return TimeTracker(self.time - other)
