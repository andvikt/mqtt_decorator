import asyncio
from datetime import datetime
from functools import wraps
from typing import Callable, Union, Awaitable, Any
from .state import StateTracker
from .utils.utils import TimeTracker, CustomTime

_LOOPS = []

RuleType = Union[asyncio.Condition, Awaitable, StateTracker, TimeTracker]


def loop_forever(foo=None, *, start_immediate=False, once=False, **kwargs):
    """
    Wraps a foo in endless while True loop
    :param foo:
    :param start_immediate: if True, immediatly ensure_future, return Future object
    :param once: if True, end execution as soon as awaited
    :return:
    """
    def deco(foo):
        assert asyncio.iscoroutinefunction(foo), f'Loop forever can decorate only async functions'
        @wraps(foo)
        async def wrapper(*args, **kwargs):
            try:
                while True:
                    if asyncio.iscoroutinefunction(foo):
                        await foo(*args, **kwargs)
                    elif asyncio.iscoroutine(foo):
                        await foo
                    elif isinstance(foo, Callable):
                        foo(*args, **kwargs)
                    if once:
                        _LOOPS.remove(ftr)
                        return
            except asyncio.CancelledError:
                _LOOPS.remove(ftr)

        if start_immediate:
            ftr =  asyncio.ensure_future(wrapper(**kwargs))
            _LOOPS.append(ftr)
            return ftr
        return wrapper
    return deco if foo is None else deco(foo)


def get_awaitable(foo: Union[RuleType, Callable[[], RuleType]]) -> Awaitable:
    if isinstance(foo, asyncio.Condition):
        return foo.wait()
    elif isinstance(foo, Awaitable):
        return foo
    elif isinstance(foo, StateTracker):
        return foo.cond
    elif isinstance(foo, TimeTracker):
        return foo.wait()
    elif isinstance(foo, Callable):
        return get_awaitable(foo())
    else:
        raise TypeError(f'Rule does not support {foo} of type: {type(foo)}')


def rule(cond: Union[RuleType, Callable[[], RuleType]], once=False):
    """
    Rule-decorator
    When foo is decorated with rule, it is sheduled to run in endless loop awating on event
        , each time event triggers
        , foo is called
    :param cond: condition for rule to be triggered. It can be:
        - :class:`asyncio.Condition`, in that case rule will wait for
            it in endless loop or once if once is True.
        - typing.Awaitable, in that case rule will await cond on each loop
        - utils.StateTracker, will wait for StateTracker.cond
        - Callable - factory, returning Awaitable, Condition or StateTracker. Will use that factory on each loop for
            getting new condition
    :param once: if True, rule will be triggered only once, forced if con is instance of TimeTracker
    :param wait_for: if passed, wait_for will be used instead of wait, wait_for will be passed to wait_for
    :return: asyncio.Task, can be cancelled later
    """
    if isinstance(once, TimeTracker):
        once=True
    def deco(foo):
        assert asyncio.iscoroutinefunction(foo), f'Rule can decorate only async functions'
        @loop_forever(start_immediate=True, once=once)
        async def wrap():
            async with cond:
                await get_awaitable(cond)
        return wrap
    return deco


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
                if (CustomTime.now() - last_time).seconds >= max_wait:
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
