import asyncio
from functools import wraps
from typing import Callable, List
import warnings
import attr
import typing


@attr.s
class loop_forever:
    """
    Wraps a foo in endless while True loop
    :param foo:
    :param start_immediate: if True, immediatly ensure_future, return Future object
    :param once: if True, end execution as soon as awaited
    :return:
    """
    foo: Callable=attr.ib(default=None)
    comment: str = attr.ib(default=None)
    start_immediate:bool=attr.ib(default=False, kw_only=True)
    once:bool=attr.ib(default=False, kw_only=True)
    foo_kwargs: dict = attr.ib(factory=dict, kw_only=True)
    started: asyncio.Event = attr.ib(factory=asyncio.Event, init=True, kw_only=True)
    self_forward: bool = attr.ib(default=False, kw_only=True) # if True, move self as argument to foo
    stob_cb: typing.Awaitable = attr.ib(default=None, kw_only=True)


    _task: asyncio.Future = None
    _wrapper: Callable = None
    _closed: asyncio.Event = attr.ib(factory=asyncio.Event, init=False)
    _paused = False

    paused = attr.ib(default=False, kw_only=True)
    resumed: asyncio.Condition = attr.ib(factory=asyncio.Condition, init=False)

    def __attrs_post_init__(self):
        self._child_loops: List[loop_forever] = []

    def __call__(self, foo=None):
        foo = foo or self.foo
        if foo is None:
            raise TypeError(f'foo of {self} is none')
        assert asyncio.iscoroutinefunction(foo), f'Loop forever can decorate only async functions'
        @wraps(foo)
        async def wrapper(*args, **kwargs):
            if self.self_forward:
                args = tuple([self, *args])
            else:
                self.started.set()
            try:
                while True:
                    async with self.resumed:
                        if self.paused:
                            await self.resumed.wait()
                            self.paused = False
                    if asyncio.iscoroutinefunction(foo):
                        await foo(*args, **kwargs)
                    elif asyncio.iscoroutine(foo):
                        await foo
                    elif isinstance(foo, Callable):
                        foo(*args, **kwargs)
                    if self.once:
                        return
            except asyncio.CancelledError:
                pass
            except Exception as err:
                warnings.warn(f'Error while closing loop: {err}')
            finally:
                if self.stob_cb:
                    if isinstance(self.stob_cb, typing.Awaitable):
                        await self.stob_cb
                    elif isinstance(self.stob_cb, Callable):
                        self.stob_cb()
                self._closed.set()

        self._wrapper = wrapper
        if self.start_immediate:
            warnings.warn('Do not use start_immediate==True', DeprecationWarning)
            self._task = asyncio.ensure_future(self.start())
        return self

    async def pause(self):
        async with self.resumed:
            self.paused = True

    async def resume(self):
        async with self.resumed:
            self.resumed.notify_all()

    async def start(self):
        if self._task is not None:
            warnings.warn('already started')
        else:
            self._task = asyncio.create_task(self._wrapper(**self.foo_kwargs))
        await self.wait_started()
        return self._task

    async def wait_started(self):
        done, notdone = await asyncio.wait([self.started.wait()], timeout=5)
        if notdone:
            exc = self._task.exception()
            if exc:
                raise exc
            raise RuntimeError(f'{notdone} is not finished in 5 seconds')

    async def close(self):
        if not self.started.is_set():
            warnings.warn(f'{self} is not started yet, but is tring to close')
            return
        if self._task:
            self._task.cancel()
        done, pend = await asyncio.wait([self._closed.wait()], timeout=5)
        if pend:
            warnings.warn(f'Could not close tasks properly')
            exc = None
            try:
                exc = self._task.exception()
            except:
                pass
            if exc:
                raise exc