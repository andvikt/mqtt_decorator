import asyncio
import warnings
from threading import Lock as ThreadLock
from typing import List, Dict

import attr

from .rules import loop_forever, rule
from .const import _T, logger
from .core import start_callback
from . import utils


@attr.s
class Thing(object):

    root = ''

    def __attrs_post_init__(self):
        from .state import State

        if not asyncio.get_event_loop().is_running():
            warnings.warn('Do not init things outside event loop', DeprecationWarning)
        from .app import App
        from .bindings.binding import Binding
        self.push_bindings: List[Binding] = []
        self.request_bindings: List[Binding] = []
        self.data_lock = asyncio.Lock()
        self.thread_lock = ThreadLock()
        self.que = asyncio.Queue()
        self.name = None
        self._app: App = None
        self._bindings: List[Binding] = []
        self.states: Dict[str, State] = {}
        self.start_callbacks = []
        self.changed = asyncio.Condition()

        for name, x in self.__dict__.items():
            if isinstance(x, State):
                x.thing = self
                x.name = name
                self.states[name] = x

                @rule(x.changed)
                async def listen_states():
                    async with self.changed:
                        self.changed.notify_all()

    @loop_forever
    async def _loop(self):
        await self.loop()

    async def loop(self):
        await asyncio.sleep(1)

    @property
    def app(self):
        if self._app is None:
            raise RuntimeError('app is not set for')
        return self._app

    def bind(self, binding: _T, *args, **kwargs):
        warnings.warn('Bind will be replaced with bind_to', DeprecationWarning)
        self._bindings.append((binding, args, kwargs))
        return self

    @start_callback
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
        from .bindings import Binding
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
                else:
                    _event = x.received_command

                @rule(_event)
                async def push():
                    await binding.push(x)

            # subscribe
            if subscribe:
                binding.subscriptions[(self.unique_id, n)] = x
        return self

    @classmethod
    def get_states(cls):
        return {
            n: x for n, x in cls.__dict__.items() if isinstance(x, State)
        }

    def __set_name__(self, owner, name):
        self.name = name
        self.owner: type = owner

    @property
    def unique_id(self):
        return f'{self.root}.{self.name}'


    def validate_args(self, data):
        assert set(data.keys()).issubset(set(self.states.keys()))\
            , f'{self} dont have states: {set(data.keys()) - set(self.get_states().keys())}'

    def as_json(self):
        return {n: x.value for n, x in self.states.items()}

    async def start(self):
        asyncio.ensure_future(self._loop())
        for x in self.start_callbacks:
            x()

    def __str__(self):
        return f'{self.__class__.__name__}.{self.name} with State:  {self.as_json()}'