import asyncio
from typing import Callable, Union, Awaitable, Any
import typing
from contextlib import asynccontextmanager, AbstractAsyncContextManager

from .utils.utils import loop_forever, mark
from .utils.utils import TimeTracker, CustomTime, _is_rule
from asyncio_primitives import utils as async_utils, CustomCondition
from .state import State
from functools import wraps
from asyncio_primitives import utils as async_utils

_LOOPS = []

RuleType = Union[asyncio.Condition, Awaitable, TimeTracker]


def rule(state: State):
    return state.rule()


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
