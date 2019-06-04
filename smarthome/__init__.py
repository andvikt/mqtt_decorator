import asyncio
import json
from typing import TypeVar, cast, List, Tuple, Callable, Any, Generic, Dict, Union
from logging import getLogger
from threading import Lock as ThreadLock
import functools
from dataclasses import dataclass, field
from copy import copy
import attr
import warnings
from . import utils

_T = TypeVar('_T')
_ThingT = TypeVar('_ThingT')
logger = getLogger(__name__)

CHANGE = 'update'
COMMAND = 'command'


class Thing(object):

    root = ''

    def __new__(cls, *args, **kwargs):
        if not asyncio.get_event_loop().is_running():
            warnings.warn('Will raise Error', DeprecationWarning)
        from .app import App
        from .bindings.binding import Binding
        obj = object.__new__(cls)
        obj.push_bindings: List[Binding] = []
        obj.request_bindings: List[Binding] = []
        obj.data_lock = asyncio.Lock()
        obj.thread_lock = ThreadLock()
        obj.que = asyncio.Queue()
        obj.name = None
        obj._app: App = None
        obj._init_args = args
        obj._init_kwargs = kwargs
        obj._bindings: List[Binding] = []
        obj.states: Dict[str, State] = {}
        obj.start_callbacks = []
        for name, x in cls.__dict__.items():
            if isinstance(x, State):
                cp = copy(x)
                cp.thing = obj
                cp.name = name
                setattr(obj, name, cp)
                obj.states[name] = cp
        return obj

    @property
    def app(self):
        if self._app is None:
            raise RuntimeError('app is not set for')
        return self._app

    def bind(self, binding: _T, *args, **kwargs):
        warnings.warn('Bind will be replaced with bind_to', DeprecationWarning)
        self._bindings.append((binding, args, kwargs))
        return self

    @utils.start_callback
    def bind_to(self, binding, push=True, subscribe=True, event='change', *states):
        """
        Bind thing to binding
        :param binding:
        :param push: if True, will push states to binding
        :param subscribe: if True, will subscribe to bindig
        :param event: str, event that will trigger pushed, can be ['change', 'update', 'command']
        :param states: if supplied, will push/subscribe only to those states
        :return:
        """
        from .bindings.binding import Binding
        binding: Binding = binding
        states = states or tuple(self.states.keys())
        assert set(states).issubset(set(self.states.keys()))
        assert event in ['change', 'update', 'command']

        for n, x in utils.dict_in(self.states, *states):
            # push
            if push:
                if event == 'change':
                    _event = x.changed
                elif event == 'update':
                    _event = x.received_update
                elif event == 'command':
                    _event = x.received_command

                @utils.loop_forever(start_immediate=True)
                async def push():
                    async with _event:
                        await _event.wait()
                        await binding.push(x)
            # subscribe
            if subscribe:
                binding.subscriptions[(self.unique_id, n)] = x
        return self


    def __init__(self, *, bindings: list=None):
        for x in (bindings or []):
            x(self)

    @classmethod
    def get_states(cls):
        return {
            n: x for n, x in cls.__dict__.items() if isinstance(x, State)
        }

    def __hash__(self):
        return hash(self.unique_id)

    def __eq__(self, other):
        if isinstance(other, Thing):
            return self.unique_id == other.unique_id
        elif isinstance(other, str):
            return self.unique_id == other
        else:
            return False

    def __set_name__(self, owner, name):
        self.name = name
        self.owner: type = owner

    @property
    def unique_id(self):
        return f'{self.root}.{self.name}'

    async def push(self, from_binding=None):
        warnings.warn('', DeprecationWarning)
        logger.debug(f'{self} begin push')
        def wrap():
            for binding in self.push_bindings:
                if binding.eho_safe or binding is not from_binding:
                    yield self.app.async_run(binding.push, self)
        await asyncio.gather(*wrap())

    def validate_args(self, data):
        assert set(data.keys()).issubset(set(self.states.keys()))\
            , f'{self} dont have states: {set(data.keys()) - set(self.get_states().keys())}'

    async def async_update(self, data: dict, from_binding=None):
        warnings.warn('', DeprecationWarning)
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
        warnings.warn('', DeprecationWarning)
        while True:
            await self.async_update(data=await self.que.get())

    async def sync_update(self, data: dict):
        warnings.warn('', DeprecationWarning)
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
        return {n: x.value for n, x in self.states.items()}

    async def start(self):
        for x in self.start_callbacks:
            x()
        await self.request_data()

    def __repr__(self):
        return f'{self}'

    def __str__(self):
        return f'{self.__class__.__name__}.{self.name} with State:  {self.as_json()}'


@dataclass
class State(Generic[_T]):
    """
    Represents one of Thing's state, when called change, command or update,
    then Events are triggered accordingly, notifying all the subscribers
    """
    converter: Callable[[str], _T]
    value: _T = None
    thing: Union[Thing, _ThingT] = field(default=None, init=False, repr=True)
    name: str = field(default=None, init=False, repr=True)
    changed: asyncio.Condition = field(default_factory=asyncio.Condition, init=False, repr=False)
    received_update: asyncio.Condition = field(default_factory=asyncio.Condition, init=False, repr=False)
    received_command: asyncio.Condition = field(default_factory=asyncio.Condition, init=False, repr=False)

    async def change(self, value: _T, _from: object = None):
        async with self.changed:
            if isinstance(value, str):
                value = self.converter(value)
            if self.value != value:
                logger.debug(f'Change {self.thing.unique_id}.{self.name} from {self.value} to {value}')
                self.value = value
                self.changed.notify_all()
                return True
            else:
                return False

    async def command(self, value: _T, _from: object = None):
        logger.debug(f'Command recieved for {self.thing.unique_id}.{self.name}')
        async with self.received_command:
            await self.change(value)
            self.received_command.notify_all()

    async def update(self, value: _T, _from: object = None):
        logger.debug(f'Update recieved for {self.thing.unique_id}.{self.name}')
        async with self.received_update:
            await self.change(value)
            self.received_command.notify_all()
