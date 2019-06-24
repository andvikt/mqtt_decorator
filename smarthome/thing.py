import asyncio
import warnings
from threading import Lock as ThreadLock
from typing import List, Dict
import typing

import attr

from .rules import rule
from .const import _T, logger
from .core import start_callback
from . import utils
from .utils.mixins import _MixRules


class Group:

    def __init__(self, *things):
        self.things: typing.List[Thing] = []
        self.things.extend(things)


class Thing(_MixRules):

    root = ''

    def __init__(self, *args):
        from .state import State

        super().__init__()
        # add groups
        self.groups = []
        for x in args:
            if isinstance(x, Group):
                self.groups.append(x)
                x.things.append(self)

        if not asyncio.get_event_loop().is_running():
            warnings.warn('Do not init things outside event loop', DeprecationWarning)
        from .app import App
        from .bindings.binding import Binding
        self.push_bindings: List[Binding] = []
        self.request_bindings: List[Binding] = []
        self.name = None
        self._app: App = None
        self._bindings: List[Binding] = []
        self.states: Dict[str, State] = {}
        self.start_callbacks = []

        # add states
        for name, x in self.__class__.__dict__.items():
            if hasattr(x, '_state'):
                state = x()
                setattr(self, name, state)
                state.thing = self
                state.name = name
                self.states[name] = state

        for x in self.groups:
            if self not in x.things:
                x.things.append(self)

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
    def bind_to(self, binding, push=True, subscribe=True, event='change', *states, **data):
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

                @self.rule(_event)
                async def push():
                    await binding.push(x, **data)

            # subscribe
            if subscribe:
                binding.subscriptions[(self.unique_id, n)] = x
                binding.subscribe_data[(self.unique_id, n)] = data
        logger.debug(f'{self} binded to {binding}')
        return self

    @classmethod
    def get_states(cls):
        from .state import State
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

    def __str__(self):
        return f'{self.__class__.__name__}.{self.name} with State:  {self.as_json()}'


    async def start(self):
        for x in self.start_callbacks:
            if asyncio.iscoroutinefunction(x):
                await x()
            else:
                x()
        await super().start()