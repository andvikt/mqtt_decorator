from datetime import datetime, timedelta
from functools import partial
from typing import Callable, Optional, Generic
from ..const import _T, _X

import attr
from astral import Astral

from .utils import TimeTracker, CustomTime


class partial_add(Generic[_T]):

    def __init__(self, *args, **kwargs):
        self.part = partial(*args, **kwargs)
        self.add = []
        self.sub = []

    def __add__(self, other):
        self.add.append(other)

    def __sub__(self, other):
        self.sub.append(other)

    def __call__(self, *args, **kwargs) -> _T:
        ret = self.part.__call__(*args, **kwargs)
        for x in self.add:
            ret += x
        for x in self.sub:
            ret -= x
        return ret


@attr.s
class Sun:

    city_name: str = attr.ib()

    def __attrs_post_init__(self):
        self.loc = Astral().geocoder[self.city_name]

    def getter(self, name, date=None):
        date = date or CustomTime.now().date()
        next_time = self.loc.sun(date)[name]
        if next_time <= CustomTime.now():
            date = date + timedelta(days=1)
            next_time = self.loc.sun(date)[name]
        return TimeTracker(next_time)

    @property
    def sunrise(self) -> partial_add[TimeTracker]:
        return partial_add(self.getter, name='sunrise')

    @property
    def dusk(self, date=None) -> partial_add[TimeTracker]:
        return partial_add(self.getter, name='dusk')

    @property
    def sunset(self, date=None) -> partial_add[TimeTracker]:
        return partial_add(self.getter, name='sunset')

    @property
    def dawn(self, date=None) -> partial_add[TimeTracker]:
        return partial_add(self.getter, name='dawn')
