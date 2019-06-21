import typing
from .infinite_loop import loop_forever as _loop_forever
import asyncio
import attr
from ..const import _T

class _MixLoops:
    """
    MixIn for storing infinite loops, implements starting and stopping loops
    """
    _loops: typing.List[_loop_forever] = None
    _started = False

    async def start(self):
        if not self._started:
            for x in self._loops or []:
                await x.start()
            self._started = True
        else:
            return

    async def stop(self):
        for x in self._loops or []:
            await x.close()

    def loop_forever(self, *args, **kwargs)->typing.Callable[[typing.Callable], _loop_forever]:
        if self._loops is None:
            self._loops = []
        def wrapper(foo):
            assert asyncio.iscoroutinefunction(foo)
            @_loop_forever(*args, **kwargs)
            async def loop():
                await foo()
            self._loops.append(loop)
            return loop
        return wrapper


class _MixRules(_MixLoops):
    """
    MixIn for decorating inline functions as rules
    All defined rules are collected in _loops argument and started/stopped using start/stop functions
    """

    def rule(self, cond, once=False
             ):
        from ..rules import rule
        if self._loops is None:
            self._loops = []
        def wrap(foo):
            assert asyncio.iscoroutinefunction(foo)
            @rule(cond=cond)
            async def wrap_rule():
                await foo()
            self._loops.append(wrap_rule)
            return wrap_rule
        return wrap


class _HasCondition:

    cond: asyncio.Condition


class _HasValue(typing.Generic[_T]):

    _value: _T

    def __init__(self, value: _T, modifier: typing.Callable[[_T], _T]=None):
        self._value = value
        self.modifier = modifier or (lambda x: x)

    @property
    def value(self):
        if isinstance(self._value, _HasValue):
            return self.modifier(self._value.value)
        else:
            return self.modifier(self._value)

    @value.setter
    def value(self, other):
        if isinstance(self._value, _HasValue):
            self._value.value = other
        else:
            self._value = other


class _ConditionCollection(_HasCondition):

    def __init__(self, *others:asyncio.Condition, check = None):
        self.others = others
        self.check = check

    def __await__(self):
        return self.start()

    async def start(self):
        from .utils import track_conditions
        self.cond = await track_conditions(*self.others, check=self.check)


class _ConditionValue(_HasValue[_T], _ConditionCollection):

    def __init__(self, value: _T, *conditions, check=None, modifier=None):
        _HasValue.__init__(self, value, modifier)
        _ConditionCollection.__init__(self, *conditions, check=check)


class _OperatorMixin(_ConditionValue):

    @property
    def cls(self):
        return self.__class__

    def __add__(self, other):
        cls = self.cls
        if isinstance(other, _ConditionValue):
            return cls(
                self.cond, other.cond
                , value=self
                , modifier=lambda x: x + other.value)
        raise TypeError(f'{other} can not be added to {self}')

    def __sub__(self, other):
        cls = self.cls
        if isinstance(other, _ConditionValue):
            return cls(
                self.cond, other.cond
                , value=self
                , modifier=lambda x: x - other.value)
        raise TypeError(f'{other} can not be added to {self}')

    def __truediv__(self, other):
        cls = self.cls
        if isinstance(other, _ConditionValue):
            return cls(
                self.cond, other.cond
                , value=self
                , modifier=lambda x: x / other.value)
        raise TypeError(f'{other} can not be added to {self}')

    def __mul__(self, other):
        cls = self.cls
        if isinstance(other, _ConditionValue):
            return cls(
                *self.others, *other.others
                , value=self
                , modifier=lambda x: x * other.value)
        raise TypeError(f'{other} can not be added to {self}')

    def __and__(self, other):
        cls = self.cls
        if isinstance(other, _ConditionValue):
            return cls(
                *self.others, *other.others
                , value=self
                , check=lambda : self.value and other.value)
        raise TypeError(f'{other} can not be added to {self}')

    def __or__(self, other):
        cls = self.cls
        if isinstance(other, _ConditionValue):
            return cls(
                *self.others, *other.others
                , value=self
                , check=lambda : self.value or other.value)
        raise TypeError(f'{other} can not be added to {self}')