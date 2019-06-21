import asyncio
from dataclasses import dataclass, field
from typing import Generic, Callable, Union

from .const import _T, logger, _ThingT

import attr
import typing
import inspect
from copy import copy
from itertools import chain
from .utils.infinite_loop import loop_forever
from .utils.mixins import _MixRules, _MixLoops
from .utils.condition_any import ConditionAny
from asyncio_primitives import CustomCondition, utils as async_utils
from .utils.proxy import LambdaProxy


@dataclass(eq=False)
class State(Generic[_T]):
    """
    Represents one of Thing's state, when called change, command or update,
    then Events are triggered accordingly, notifying all the subscribers

    :var check: callable, passed to rule-creator

    """
    converter: Callable[[str], _T] = field(default_factory=float)
    value: _T = 0
    thing: Union[_ThingT] = field(default=None, init=False, repr=True)
    name: str = field(default=None, init=False, repr=True)
    changed: typing.List[CustomCondition] = field(default_factory=lambda : [CustomCondition()], init=False, repr=False)
    received_update: typing.List[CustomCondition] = field(default_factory=lambda : [CustomCondition()], init=False, repr=False)
    received_command: typing.List[CustomCondition] = field(default_factory=lambda : [CustomCondition()], init=False, repr=False)
    check: typing.Callable = field(default_factory=lambda :lambda :True)


    async def change(self, value: _T, _from: object = None):
        if isinstance(value, str):
            value = self.converter(value)
        if self.value != value:
            logger.debug(f'Change {self.name} from {self.value} to {value}')
            self.value = value
            await async_utils.notify_many(*self.changed)
            return True
        else:
            return False

    async def command(self, value: _T, _from: object = None):
        logger.debug(f'Command recieved for {self.thing.unique_id}.{self.name}')
        await self.change(value)
        await async_utils.notify_many(*self.received_command)

    async def update(self, value: _T, _from: object = None):
        logger.debug(f'Update recieved for {self.thing.unique_id}.{self.name}')
        await self.change(value)
        await async_utils.notify_many(*self.received_update)

    async def notify_changed(self):
        await async_utils.notify_many(*self.changed)

    def rule(self):
        return async_utils.rule(*self.changed, check=self.check)

    def __add__(self, other):
        if isinstance(other, State):
            return self.make_proxy(value=lambda x: x + other.value, y=other)
        else:
            return self.make_proxy(value=lambda x: x + other)

    def __sub__(self, other):
        if isinstance(other, State):
            return self.make_proxy(value=lambda x: x - other.value, y=other)
        else:
            return self.make_proxy(value=lambda x: x - other)

    def __truediv__(self, other):
        if isinstance(other, State):
            return self.make_proxy(value=lambda x: x / other.value, y=other)
        else:
            return self.make_proxy(value=lambda x: x / other)

    def __mul__(self, other):
        if isinstance(other, State):
            return self.make_proxy(value=lambda x: x * other.value, y=other)
        else:
            return self.make_proxy(value=lambda x: x * other)

    def __eq__(self, other):
        if isinstance(other, State):
            return self.make_proxy(check=lambda: self.value == other.value, y=other)
        else:
            return self.make_proxy(check=lambda: self.value == other)

    def __ne__(self, other):
        if isinstance(other, State):
            return self.make_proxy(check=lambda: self.value != other.value, y=other)
        else:
            return self.make_proxy(check=lambda: self.value != other)

    def __le__(self, other):
        if isinstance(other, State):
            return self.make_proxy(check=lambda: self.value <= other.value, y=other)
        else:
            return self.make_proxy(check=lambda: self.value <= other)

    def __lt__(self, other):
        if isinstance(other, State):
            return self.make_proxy(check=lambda: self.value < other.value, y=other)
        else:
            return self.make_proxy(check=lambda: self.value < other)

    def __ge__(self, other):
        if isinstance(other, State):
            return self.make_proxy(check=lambda: self.value >= other.value, y=other)
        else:
            return self.make_proxy(check=lambda: self.value >= other)

    def __gt__(self, other):
        if isinstance(other, State):
            return self.make_proxy(check=lambda: self.value > other.value, y=other)
        else:
            return self.make_proxy(check=lambda: self.value > other)

    def __and__(self, other):
        if isinstance(other, State):
            return self.make_proxy(check=lambda: self.check() and other.check(), y=other)
        else:
            return self.make_proxy(check=lambda: self.check() and other)

    def __or__(self, other):
        if isinstance(other, State):
            return self.make_proxy(check=lambda: self.check() or other.check(), y=other)
        else:
            return self.make_proxy(check=lambda: self.check() or other)


    def make_proxy(self
                   , value: typing.Union[typing.Callable[[_T], _T], _T] = None
                   , y = None
                   , check = None):
        """
        Make proxy for State. Replace value with lambda, adds conditions from other if other is State
        :param x:
        :param value:
        :param y:
        :param check:
        :return:
        """
        kwargs = {}


        if check:
            def new_check():
                return self.check() and check()
            kwargs['check'] = lambda x: new_check

        if value is not None:
            kwargs['value'] = value

        if isinstance(y, State):
            kwargs.update(
                changed=self.changed + y.changed
                , received_update=self.received_update + y.received_update
                , received_command=self.received_command + y.received_command)

        return typing.cast(self.__class__, LambdaProxy(self, **kwargs))
