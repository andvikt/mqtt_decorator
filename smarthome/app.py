from concurrent.futures.thread import ThreadPoolExecutor
import asyncio

from .thing import Thing
from .bindings.binding import Binding
import typing
from .const import logger, Logger
import types
import typing
from asyncio_primitives import utils as autils

logger = logger.getChild('app')

class App(object):

    name: str = 'app'

    def __init__(self):
        from . import Thing
        from .bindings.binding import Binding
        self.threadPool = ThreadPoolExecutor()
        self._loop = asyncio.get_event_loop()
        self.started = asyncio.Event()
        for n, x in self.__class__.__dict__.items():
            if isinstance(x, (Thing, Binding)):
                x._app = self
        self._things: typing.List[Thing] = [getattr(self, x) for x, v in self.__class__.__dict__.items() if isinstance(v, Thing)]
        self._bindings: typing.List[Binding] = [getattr(self, x) for x, v in self.__class__.__dict__.items() if isinstance(v, Binding)]
        self._task_starters = []
        self._tasks = []

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def get_things(self) -> typing.List[Thing]:
        return self._things

    def get_bindings(self) -> typing.List[Binding]:
        return typing.cast(
            typing.List[Binding]
            , self._bindings
        )

    async def start(self):
        lck = asyncio.Lock()

        async def start_starter(name, starter):
            task = await starter()
            logger.debug(f'{name} is started')
            async with lck:
                self._tasks.append(task)

        for x in self.get_things():
            x._app = self
            await x.start()

        for x in self.get_bindings():
            x._app = self
            await x._start()

        if self._task_starters:
            await asyncio.gather(*[start_starter(n, x) for n, x in self._task_starters])

        logger.info(f'{self} started!')

    async def stop(self):
        from .utils.utils import cancel_tasks
        for x in self.get_bindings():
            logger.debug(f'Stop binding {x.name}')
            await x._stop()

        for x in self._things:
            await x.stop()

        await cancel_tasks(*self._tasks)

        logger.debug(f'{self.name} stopped')

    @classmethod
    async def from_module(cls, name, mod: types.ModuleType):
        new_app = cls()
        new_app.name = name
        starters = {}
        lck = asyncio.Lock()
        for roots, name, val in item_load(mod):
            _name = '.'.join(roots[1:] + [name])
            if isinstance(val, (Thing, Binding)):
                val._app = new_app
                val.name = _name
                if isinstance(val, Thing):
                    new_app._things.append(val)
                if isinstance(val, Binding):
                    new_app._bindings.append(val)
            if isinstance(val, asyncio.Task):
                new_app._tasks.append(val)
            elif autils.is_starter(val):
                new_app._task_starters.append((name, val))

        return new_app


def item_load(mod: types.ModuleType, roots: list = None):
    roots = roots or []
    skiproot = mod.__dict__.get('__skiproot__', False)
    if not skiproot:
        roots = roots + [mod.__name__]

    for name, val in mod.__dict__.items():
        from . import Thing
        from .bindings.binding import Binding
        if isinstance(val, (Thing, Binding, asyncio.Task)):
            yield roots, name, val
        elif getattr(val, '__isconf__', False):
            yield from item_load(val, roots)
        elif autils.is_starter(val):
            yield roots, name, val