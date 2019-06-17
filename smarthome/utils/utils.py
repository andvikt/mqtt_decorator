import asyncio
from datetime import datetime, timedelta
from typing import Dict, Generator, Tuple
import typing
import warnings

import attr

from ..const import _X, _T

ASYNC_RUN_FOO = typing.Union[
            typing.Awaitable[_T]
            , typing.Callable[[], typing.Union[_T, typing.Awaitable[_T]]]
        ]


async def async_run(foo: ASYNC_RUN_FOO, *args, **kwargs):
    """
    Helps run async functions, coroutines, sync-callable in a single manner
    :param foo:
    :param args: will be passed to foo if it is function
    :param kwargs: will be passed to foo if it is function
    :return:
    """
    if asyncio.iscoroutinefunction(foo):
        return await foo(*args, **kwargs)
    elif asyncio.iscoroutine(foo):
        return await foo
    elif isinstance(foo, typing.Callable):
        return foo(*args, **kwargs)
    else:
        return foo


async def wait_started(foo: ASYNC_RUN_FOO, cancel_callback: ASYNC_RUN_FOO = None) -> asyncio.Task:
    """
    Helps to run some foo
    :param foo: some async function or coroutine
    :param cancel_callback:
    :return:
    """
    started = asyncio.Event()

    async def wrap():
        started.set()
        try:
            await async_run(foo)
        except asyncio.CancelledError:
            pass
        finally:
            await async_run(cancel_callback)

    ret = asyncio.create_task(wrap())
    await started.wait()
    return mark(ret, markers=['_for_cancel'])


def mark(foo=None, *, markers: typing.Iterable[str]):
    """
    Add some markers to foo
    :param foo: any object
    :param args: some str markers
    :return:
    """
    def deco(_foo):
        for x in markers:
            try:
                setattr(_foo, x, True)
            except AttributeError:
                raise
        return _foo
    return deco(foo) if foo is not None else deco


def loop_forever(foo: ASYNC_RUN_FOO = None, *, cancel_cb: ASYNC_RUN_FOO = None):
    """
    Decorator, runs async function or coroutine in a endless loop
    :param foo:
    :param cancel_cb:
    :return:
    """

    def deco(_foo):
        async def run():
            if not (asyncio.iscoroutine(_foo) or asyncio.iscoroutinefunction(_foo)):
                raise TypeError('loop_forever can handle only async functions or coroutines')

            async def wrap():
                fast_loop_count = 0
                while True:
                    time = datetime.now()
                    await async_run(_foo)
                    if (datetime.now() - time).total_seconds() <= 0.1:
                        fast_loop_count+=1
                    if fast_loop_count >= 100:
                        warnings.warn(f'{_foo} is run in endless loop very fast')

            return await wait_started(wrap(), cancel_callback=cancel_cb)
        return mark(run(), markers=['_is_loop'])
    return deco(foo) if foo is not None else deco


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
