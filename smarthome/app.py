from concurrent.futures.thread import ThreadPoolExecutor
import asyncio
from inspect import isawaitable
from . import Thing
from .bindings.binding import Binding
import typing
from logging import getLogger
from functools import partial
from asyncio.queues import Queue
from threading import Lock

logger = getLogger(__name__)


class App(object):

    things = []
    name: str = 'app'

    def __init__(self):
        self.threadPool = ThreadPoolExecutor()
        self._loop = asyncio.get_event_loop()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    async def async_run(self, foo, *args, **kwargs):
        """
        Run foo until it returns not an awaitable object
        :param foo:
        :param args:
        :param kwargs:
        :return:
        """
        if asyncio.iscoroutinefunction(foo):
            foo = foo(*args, **kwargs)
        elif not isawaitable(foo):
            foo = self.loop.run_in_executor(self.threadPool, partial(foo, *args, **kwargs))
        while isawaitable(foo):
            foo = await foo
        return foo

    def shedule_async_run(self, coro):
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def get_things(self) -> typing.List[Thing]:
        return [getattr(self, x) for x, v in self.__class__.__dict__.items() if isinstance(v, Thing)]

    def get_bindings(self) -> typing.List[Binding]:
        return typing.cast(
            typing.List[Binding]
            , [getattr(self, x) for x, v in self.__class__.__dict__.items() if isinstance(v, Binding)]
        )

    async def _start(self):
        for x in self.get_things():
            x.start_bindings()
        await asyncio.gather(*[x._start() for x in self.get_bindings()])
        logger.info(f'{self} started!')

    def start(self):
        self.loop.create_task(self._start())
        self.loop.run_forever()


