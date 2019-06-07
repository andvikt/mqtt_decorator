import asyncio
from dataclasses import dataclass, field
from typing import Generic, Callable, Union

from .const import _T, logger, _ThingT

import attr
import typing
from itertools import chain


@dataclass
class State(Generic[_T]):
    """
    Represents one of Thing's state, when called change, command or update,
    then Events are triggered accordingly, notifying all the subscribers
    """
    converter: Callable[[str], _T]
    value: _T = None
    thing: Union[_ThingT] = field(default=None, init=False, repr=True)
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

    def __eq__(self, other):
        def check():
            if isinstance(other, State):
                return self.value == other.value
            else:
                return self.value == other
        return StateTracker((self,), check)

    def __ne__(self, other):
        def check():
            if isinstance(other, State):
                return self.value != other.value
            else:
                return self.value != other

        return StateTracker((self,), check)

    def __le__(self, other):
        def check():
            if isinstance(other, State):
                return self.value <= other.value
            else:
                return self.value <= other

        return StateTracker((self,), check)

    def __lt__(self, other):
        def check():
            if isinstance(other, State):
                return self.value < other.value
            else:
                return self.value < other

        return StateTracker((self,), check)

    def __ge__(self, other):
        def check():
            if isinstance(other, State):
                return self.value >= other.value
            else:
                return self.value >= other

        return StateTracker((self,), check)

    def __gt__(self, other):
        def check():
            if isinstance(other, State):
                return self.value > other.value
            else:
                return self.value > other

        return StateTracker((self,), check)


@attr.s
class StateTracker(object):
    """
    Tracks given states and trigger self.cond if some state changes and check callable returns True
    """
    states: typing.Iterable[State] = attr.ib()
    check: typing.Callable[[], bool] = attr.ib()
    _cond: asyncio.Condition = None

    def __and__(self, other):
        if not isinstance(other, StateTracker):
            raise TypeError()
        return StateTracker(chain(self.states, other), lambda : self.check() and other.check())

    def __or__(self, other):
        if not isinstance(other, StateTracker):
            raise TypeError()
        return StateTracker(chain(self.states, other), lambda : self.check() or other.check())

    @property
    def cond(self) -> asyncio.Condition:
        from .rules import rule

        if self._cond is None:
            self._cond = cond = asyncio.Condition()
            for x in self.states:
                @rule(x.changed)
                async def trigger():
                    async with cond:
                        if self.check():
                            cond.notify_all()

        return self._cond

