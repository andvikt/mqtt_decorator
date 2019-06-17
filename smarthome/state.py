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


class OperatorMixin:

    track_other_states: typing.List = None

    def modificate(self, modif, state=None):

        return StateModificator(source=self
                                , modif=modif
                                , other=state
                                , track_other_states=self.track_other_states)

    def __add__(self, other):
        if isinstance(other, State):
            return self.modificate(lambda x: x + other.value, other)
        else:
            return self.modificate(lambda x: x + other)

    def __sub__(self, other):
        if isinstance(other, State):
            return self.modificate(lambda x: x - other.value, other)
        else:
            return self.modificate(lambda x: x - other)

    def __truediv__(self, other):
        if isinstance(other, State):
            return self.modificate(lambda x: x / other.value, other)
        else:
            return self.modificate(lambda x: x / other)

    def __mul__(self, other):
        if isinstance(other, State):
            return self.modificate(lambda x: x * other.value, other)
        else:
            return self.modificate(lambda x: x * other)

@dataclass
class State(Generic[_T], OperatorMixin):
    """
    Represents one of Thing's state, when called change, command or update,
    then Events are triggered accordingly, notifying all the subscribers
    """
    converter: Callable[[str], _T]
    _value: _T = None
    thing: Union[_ThingT] = field(default=None, init=False, repr=True)
    name: str = field(default=None, init=False, repr=True)
    changed: asyncio.Condition = field(default_factory=asyncio.Condition, init=False, repr=False)
    received_update: asyncio.Condition = field(default_factory=asyncio.Condition, init=False, repr=False)
    received_command: asyncio.Condition = field(default_factory=asyncio.Condition, init=False, repr=False)
    modificator: Callable[[_T], _T] = None

    @property
    def value(self) -> _T:
        if self.modificator:
            return self.modificator(self._value)
        else:
            return self._value

    async def change(self, value: _T, _from: object = None):
        async with self.changed:
            if isinstance(value, str):
                value = self.converter(value)
            if self._value != value:
                logger.debug(f'Change {self.name} from {self._value} to {value}')
                self._value = value
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

    def __eq__(self, other):
        def check():
            if isinstance(other, State):
                return self.value == other.value
            else:
                return self.value == other
        if isinstance(other, State):
            conds = [self, other]
        else:
            conds = [self]

        return StateTracker(conds, check)

    def __ne__(self, other):
        def check():
            if isinstance(other, State):
                return self.value != other.value
            else:
                return self.value != other
        if isinstance(other, State):
            conds = [self, other]
        else:
            conds = [self]

        return StateTracker(conds, check)

    def __le__(self, other):
        def check():
            if isinstance(other, State):
                return self.value <= other.value
            else:
                return self.value <= other

        if isinstance(other, State):
            conds = [self, other]
        else:
            conds = [self]

        return StateTracker(conds, check)

    def __lt__(self, other):
        def check():
            if isinstance(other, State):
                return self.value < other.value
            else:
                return self.value < other

        if isinstance(other, State):
            conds = [self, other]
        else:
            conds = [self]

        return StateTracker(conds, check)

    def __ge__(self, other):
        def check():
            if isinstance(other, State):
                return self.value >= other.value
            else:
                return self.value >= other

        if isinstance(other, State):
            conds = [self, other]
        else:
            conds = [self]

        return StateTracker(conds, check)

    def __gt__(self, other):
        def check():
            if isinstance(other, State):
                return self.value > other.value
            else:
                return self.value > other

        if isinstance(other, State):
            conds = [self, other]
        else:
            conds = [self]

        return StateTracker(conds, check)


@attr.s
class StateTracker(_MixRules):
    """
    Tracks given states and trigger self.cond if some state changes and check callable returns True
    """
    states: typing.List[State] = attr.ib()
    conditions: typing.List[asyncio.Condition] = attr.ib(factory=list, init=False)
    check: typing.Callable[[], bool] = attr.ib()
    _cond: ConditionAny = None


    def __attrs_post_init__(self):
        for x in self.states:
            self.conditions.append(x.changed)
            for s in (x.track_other_states or []):
                if s.changed not in self.conditions:
                    self.conditions.append(s.changed)

    def __and__(self, other):
        if isinstance(other, StateTracker):
            return StateTracker(self.states + other.states, lambda : self.check() and other.check())
        elif isinstance(other, Callable):
            sig = inspect.signature(other)
            if len(sig.parameters) > 0:
                raise ValueError(f'{other} must be a callable with no arguments')
            if asyncio.iscoroutinefunction(other):
                raise TypeError(f'{other} is coroutinefunction')
            return StateTracker(self.states, lambda : self.check() and other())
        else:
            raise TypeError(f'{type(other)} argument is not supported in &| operators of StateTracker')

    def __or__(self, other):
        if isinstance(other, StateTracker):
            return StateTracker(self.states + other.states, lambda: self.check() or other.check())
        elif isinstance(other, Callable):
            sig = inspect.signature(other)
            if len(sig.parameters) > 0:
                raise ValueError(f'{other} must be a callable with no arguments')
            if asyncio.iscoroutinefunction(other):
                raise TypeError(f'{other} is coroutinefunction')
            return StateTracker(self.states, lambda: self.check() or other())
        else:
            raise TypeError(f'{type(other)} argument is not supported in &| operators of StateTracker')

    @property
    def cond(self) -> ConditionAny:
        if self._cond is None:
            self._cond = ConditionAny(self.conditions, check=self.check)
        return self._cond

    async def start(self):
        await self.cond.start()
        for x in self.states:
            if isinstance(x, _MixLoops):
                await x.start()
        await super().start()

    async def stop(self):
        for x in self.states:
            if isinstance(x, StateModificator):
                await x.stop()
        await self.cond.stop()
        await super().stop()


@attr.s
class StateModificator(_MixRules):

    source: typing.Union[State, OperatorMixin] = attr.ib()
    modif: typing.Callable = attr.ib()
    other: State = attr.ib(default=None)
    track_other_states: typing.List[State] = attr.ib(default=None)
    _cond: ConditionAny = None

    def __attrs_post_init__(self):
        if self.track_other_states is not None and self.other is not None:
            self.track_other_states = self.track_other_states + [self.other]
        elif self.other is not None:
            self.track_other_states = [self.other]

    def value(self):
        return self.modif(self.source._value)

    def __getattribute__(self, item):
        try:
            return object.__getattribute__(self, item)
        except AttributeError:
            return getattr(self.source, item)

    @property
    def changed(self) -> ConditionAny:
        if self._cond is None:
            self._cond = ConditionAny([
                x.changed for x in [self.source] + self.track_other_states
            ])
        return self._cond

    async def start(self):
        await self._cond.start()
        await super().start()

    async def stop(self):
        await self._cond.stop()
        await super().stop()
