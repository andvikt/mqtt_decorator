import asyncio
from datetime import datetime, timedelta
from typing import Dict, Generator, Tuple
import typing
import warnings
from functools import wraps

import attr
from inspect import signature, Parameter
from asyncio_primitives import utils as autils

from ..const import _X, _T, logger

ASYNC_RUN_FOO = typing.Union[
            typing.Awaitable[_T]
            , typing.Callable[[], typing.Union[_T, typing.Awaitable[_T]]]
        ]


async def cancel_all():
    for x in asyncio.all_tasks():
        if hasattr(x, '_for_cancel'):
            x.cancel()
            await x


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

    def rule(self):
        """
        Make single-time rule: wait for self's time and run foo, returns async-foo, that should be called in order to start
        :return:
        """
        def deco(foo):
            @wraps(foo)
            @autils.mark_starter
            async def wrapper(*args, **kwargs):
                async def rule(started):
                    await started
                    await self.wait()
                    await autils.async_run(foo, *args, **kwargs)
                return await autils.wait_started(rule)
            return wrapper
        return deco

    @classmethod
    def repeat(cls, time_interval: timedelta):
        assert isinstance(time_interval, timedelta)

        def deco(foo):
            @wraps(foo)
            @autils.mark_starter
            async def wrapper(*args, **kwargs):
                @autils.endless_loop
                async def _loop():
                    await (cls.now() + time_interval).wait()
                    await autils.async_run(foo, *args, **kwargs)
                return await _loop()
            return wrapper
        return deco


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


async def cancel(task: asyncio.Task):
    if not (task.done() or task.cancelled()):
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass


async def cancel_tasks(*tasks: asyncio.Task):
    if tasks:
        await asyncio.gather(*[cancel(task) for task in tasks])
