import asyncio
from typing import Callable, Union, Awaitable, Any
import typing
from contextlib import asynccontextmanager, AbstractAsyncContextManager

from .utils.utils import loop_forever, mark
from .utils.utils import TimeTracker, CustomTime, _is_rule
from asyncio_primitives import utils as async_utils, CustomCondition
from .state import State

_LOOPS = []

RuleType = Union[asyncio.Condition, Awaitable, TimeTracker]


def rule(state: State):
    return state.rule()

def counting(max_count = None, max_wait=None):
    """
    Decorator. Decorated foo is called each time cond is triggered.
    Also counting number of trigerred event is passed as first argument
    :param max_count: Max count, after that counter will be set to zero
    :param max_wait: Max wait between counts in seconds
    :return:
    """

    def deco(foo: Callable[[int], Any]):
        assert asyncio.iscoroutinefunction(foo), 'counting must be async foo'
        cnt = 0
        last_time = CustomTime.now()
        async def wrap():
            nonlocal cnt
            nonlocal last_time
            if max_wait:
                if (CustomTime.now() - last_time).total_seconds() >= max_wait:
                    cnt = 0
            if max_count:
                if cnt>=max_count:
                    cnt = 0
            await foo(cnt)
            cnt += 1
            last_time = CustomTime.now()
        return wrap
    return deco


def stop_loops():
    for x in _LOOPS:
        x.cancel()
