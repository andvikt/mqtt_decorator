import asyncio
from datetime import datetime, timedelta
from typing import Dict, Generator, Tuple
import typing
import warnings

import attr
from inspect import signature, Parameter

from ..const import _X, _T, logger

ASYNC_RUN_FOO = typing.Union[
            typing.Awaitable[_T]
            , typing.Callable[[], typing.Union[_T, typing.Awaitable[_T]]]
        ]


class proxy(object):

    def __init__(self, obj: typing.Union[typing.Awaitable, typing.Callable]):
        self._obj = obj
        self._task: asyncio.Task = None
        self._started = False

    def __getattribute__(self, item):
        try:
            return object.__getattribute__(self, item)
        except AttributeError:
            return object.__getattribute__(self._obj, item)

    def __await__(self):
        return self._obj.__await__()

    def __call__(self, *args, **kwargs):
        return self._obj.__call__(*args, **kwargs)

    async def start(self):
        if not self._started:
            ret = await self
            if isinstance(ret, (asyncio.Task, asyncio.Future)):
                self._task = ret
            self._started = True
            return ret
        else:
            return self._task

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def close(self):
        return await self.stop()



class _is_loop(proxy):
    """
    Proxy coroutine so that it will pass isinstance(obj, _is_loop)
    """
    pass

class _is_rule(_is_loop):
    """
    Proxy coroutine so that it will pass isinstance(obj, _is_loop)
    """
    pass

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
        raise TypeError(f'{foo} is not callable or awaitable')

async def wait_started(foo: ASYNC_RUN_FOO
                       , cancel_callback: ASYNC_RUN_FOO = None
                       ) -> asyncio.Task:
    """
    Helps to run some foo as a task and wait for started
    :param foo: some async function or coroutine
    :param cancel_callback:
    :return:
    """
    started = asyncio.Event()

    async def start():
        started.set()

    async def wrap():
        try:
            await asyncio.gather(async_run(foo), start())
        except asyncio.CancelledError:
            logger.debug(f'{foo} cancelled')
        except Exception as err:
            logger.error(f'Exception during task execution:\n{err}')
            raise err
        finally:
            if cancel_callback:
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
        _foo = mark(_foo, markers=['_is_loop'])
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

            return await wait_started(wrap, cancel_callback=cancel_cb)
        return _is_loop(run())
    return deco(foo) if foo is not None else deco


async def cancel_all():
    for x in asyncio.all_tasks():
        if hasattr(x, '_for_cancel'):
            x.cancel()
            await x


def is_loop(foo):
    return isinstance(foo, _is_loop)
    return False


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


def track_conditions(*args: asyncio.Condition, check=None):
    """
    Coroutine-factory,
    coroutines wait for conditions and returns when any of them fires
    :param args: conditions
    :param check: Callable, Awaitable, Async foo, if provided called before triggering then triggers only if True is returned
    :return:
    """
    @mark(markers=['_task_tracker'])
    async def wrapper():
        trigger = asyncio.Condition()
        for x in args:
            cond = x
            @loop_forever
            async def track():
                async with cond:
                    await cond.wait()
                    if check:
                        res = async_run(check)
                        if not res:
                            return
                async with trigger:
                    trigger.notify_all()
            await track
        return trigger
    return wrapper
