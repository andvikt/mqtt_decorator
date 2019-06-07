from concurrent.futures.thread import ThreadPoolExecutor
import asyncio

from . import rules
from .thing import Thing
from .bindings.binding import Binding
import typing
from .const import logger
import types



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
        self._things = [getattr(self, x) for x, v in self.__class__.__dict__.items() if isinstance(v, Thing)]
        self._bindings = [getattr(self, x) for x, v in self.__class__.__dict__.items() if isinstance(v, Binding)]
        self._tasks = {}

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

    async def _start(self):
        for x in self.get_things():
            x._app = self
            await x.start()
        for x in self.get_bindings():
            x._app = self

        await asyncio.gather(*[x._start() for x in self.get_bindings()])
        self.started.set()
        logger.info(f'{self} started!')

    def start(self):

        if not self.loop.is_running():
            raise RuntimeError('App must start in running loop')
        else:
            async def start():
                await self._start()
                self.bind()
            return start()

    def bind(self):
        pass

    async def stop(self):
        rules.stop_loops()
        for x in self.get_bindings():
            logger.debug(f'Stop binding {x.name}')
            if not asyncio.iscoroutinefunction(x.stop):
                x.stop()
            else:
                await x.stop()
        logger.debug(f'{self.name} stopped')

    @classmethod
    def from_module(cls, name, mod: types.ModuleType):
        new_app = cls()
        new_app.name = name
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
                new_app._tasks[_name] = val
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