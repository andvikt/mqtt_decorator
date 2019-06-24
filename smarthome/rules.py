import asyncio
from typing import Callable, Union, Awaitable
import typing

from .utils.utils import TimeTracker, CustomTime
from asyncio_primitives import utils as async_utils, CustomCondition
from .state import State
from functools import wraps

_LOOPS = []

RuleType = Union[asyncio.Condition, Awaitable, TimeTracker]

def make_onetime_rule(cond: typing.Awaitable):
    async def deco(foo):
        @wraps(foo)
        @async_utils.mark_starter
        async def wrapper(*args, **kwargs):
            async def start(started):
                await started
                await cond
                await foo(*args, **kwargs)
            return await async_utils.wait_started(start)
        return wrapper
    return deco


def rule(state: typing.Union[State, TimeTracker, Callable, Awaitable]):
    """
    Make rule from several input types:

        - State or TimeTracker: call state.rule()
        - Callable: call state first, then make Condition-rule if it returns conditions or one-time rule if it returns awaitabler
        - Awaitable: one-time rule, waits for awaitable to finish and return.
    :param state:
    :return:
    """

    if isinstance(state, (State, TimeTracker)):
        return state.rule()

    if isinstance(state, CustomCondition):
        return async_utils.rule(state)

    if isinstance(state, typing.Iterable):
            for x in state:
                assert isinstance(x, CustomCondition)
            return async_utils.rule(*state)

    if isinstance(state, Callable):
        cond = state()
        if isinstance(cond, CustomCondition):
            return async_utils.rule(cond)

        elif isinstance(cond, typing.Iterable):
            for x in cond:
                assert isinstance(x, CustomCondition)
            return async_utils.rule(*cond)

        elif isinstance(cond, typing.Awaitable):
            return make_onetime_rule(cond)

    if isinstance(state, Awaitable):
        return make_onetime_rule(state)



def counter(max_count = None, max_wait=None):
    """
    Decorator. When foo is called, passes counter as a first argument
    :param max_count: Max count, after that counter will be set to zero
    :param max_wait: Max wait between counts in seconds
    :return:
    """

    def deco(foo):
        assert asyncio.iscoroutinefunction(foo), 'counting must be async foo'
        cnt = 0
        last_time = CustomTime.now()
        @wraps(foo)
        async def wrapper(*args, **kwargs):
            nonlocal cnt
            nonlocal last_time
            if max_wait:
                if (CustomTime.now() - last_time).total_seconds() >= max_wait:
                    cnt = 0
            if max_count:
                if cnt>=max_count:
                    cnt = 0
            await async_utils.async_run(foo, cnt, *args, **kwargs)
            cnt += 1
            last_time = CustomTime.now()
        return wrapper
    return deco


def stop_loops():
    for x in _LOOPS:
        x.cancel()
