import asyncio
import json
from typing import TypeVar, cast, List, Tuple, Callable, Any
from logging import getLogger
from threading import Lock as ThreadLock
import functools

_T = TypeVar('_T')
logger = getLogger(__name__)

CHANGE = 'update'
COMMAND = 'command'

class state(object):

    def __init__(self, default=None):
        self.default = None
        self.name = None
        self.push_callbacks = []

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, f'_{self.name}', None)

    def __set_name__(self, owner, name):
        self.name = name
        self.owner = owner

    def __set__(self, instance, value):
        old_value = self.__get__(instance, None)
        if value == old_value:
            return
        logger.debug(f'set {instance}.{self.name} to {value}')
        setattr(instance, f'_{self.name}', value)

    def __str__(self):
        return f'<state> {self.owner}.{self.name}'


class ThingMeta(type):

    def __new__(cls, name, bases, args: dict):
        ret = type.__new__(cls, name, bases, args)
        ret.push_callbacks = []
        return ret


class Thing(object, metaclass=ThingMeta):

    root = ''

    def __new__(cls, *args, **kwargs):
        from .app import App
        from .bindings.binding import Binding
        obj = object.__new__(cls)
        obj.push_bindings: List[Binding] = []
        obj.request_bindings: List[Binding] = []
        obj.data_lock = asyncio.Lock()
        obj.thread_lock = ThreadLock()
        obj.que = asyncio.Queue()
        obj._app: App = None
        obj._init_args = args
        obj._init_kwargs = kwargs
        obj._bindings: List[Binding] = []
        return obj

    @property
    def app(self):
        if self._app is None:
            raise RuntimeError('app is not set for')
        return self._app

    def bind(self, binding: _T, *args, **kwargs):
        self._bindings.append((binding, args, kwargs))
        return self

    def start_bindings(self):
        for (x, args, kwargs) in self._bindings:
            x.bind(*args, thing=self, **kwargs)

    def __init__(self, *, bindings: list=None):
        for x in (bindings or []):
            x(self)

    @classmethod
    def get_states(cls):
        return {
            n: x for n, x in cls.__dict__.items() if isinstance(x, state)
        }

    def __hash__(self):
        return hash(self.unique_id)

    def __eq__(self, other):
        if isinstance(other, Thing):
            return self.unique_id == other.unique_id
        elif isinstance(other, str):
            return self.unique_id
        else:
            return False

    def __set_name__(self, owner, name):
        self.name = name
        self.owner: type = owner

    @property
    def unique_id(self):
        return f'{self.root}.{self.name}'

    async def push(self, from_binding=None):
        logger.debug(f'{self} begin push')
        def wrap():
            for binding in self.push_bindings:
                if binding.eho_safe or binding is not from_binding:
                    yield self.app.async_run(binding.push, self)
        await asyncio.gather(*wrap())

    def validate_args(self, data):
        assert set(data.keys()).issubset(set(self.get_states().keys()))\
            , f'{self} dont have states: {set(data.keys()) - set(self.get_states().keys())}'

    async def async_update(self, data: dict, from_binding=None):
        async with self.data_lock:
            self.validate_args(data)
            before = self.as_json()
            await self.before_update()
            for n, x in data.items():
                setattr(self, n, x)
            await self.after_update()
            if before != self.as_json():
                await self.push(from_binding)

    async def request_data(self):
        data = {}
        for x in self.request_bindings:
            _data = await self.app.async_run(x.thing_request, self)
            if isinstance(_data, dict):
                data.update(**_data)
        await self.async_update(data)

    async def handle_que(self):
        while True:
            await self.async_update(data=await self.que.get())

    async def sync_update(self, data: dict):
        def wrap():
            with self.thread_lock:
                return self.async_update(data)
        await self.app.async_run(wrap)

    async def before_update(self):
        """
        When bindigs update thing, they also call this method before update
        :return:
        """
        pass

    async def after_update(self):
        """
        When bindigs update thing, they also call this method before update
        :return:
        """
        pass

    def as_json(self):
        return json.dumps(
            {n: getattr(self, n) for n in self.get_states().keys()}
        )

    async def start(self):
        await self.request_data()

    def __repr__(self):
        return f'{self}'

    def __str__(self):
        return f'{self.__class__.__name__}.{self.name} with state:  {self.as_json()}'


