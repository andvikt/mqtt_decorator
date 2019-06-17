import asyncio
from typing import Callable, Union, Awaitable, Any
import typing

from .utils import loop_forever
from .utils.utils import TimeTracker, CustomTime
from .state import StateTracker

_LOOPS = []

RuleType = Union[asyncio.Condition, Awaitable, StateTracker, TimeTracker]


async def get_awaitable(foo: Union[RuleType, Callable[[], RuleType]], loop: loop_forever) \
        -> typing.Union[Awaitable, asyncio.Condition]:
    """

    :param foo:
    :param add_child: callback for adding child loop
    :return:
    """
    from .state import StateTracker
    from .utils.condition_any import ConditionAny

    if isinstance(foo, asyncio.Condition):
        return foo
    elif isinstance(foo, Awaitable):
        return foo
    elif isinstance(foo, (StateTracker, ConditionAny)):
        cond = foo.cond
        await foo.start()
        loop.stob_cb = foo.stop()
        return cond
    elif isinstance(foo, TimeTracker):
        return foo.wait()
    elif isinstance(foo, Callable):
        return await get_awaitable(foo(), loop=loop)
    else:
        raise TypeError(f'Rule does not support {foo} of type: {type(foo)}')


def rule(cond: Union[RuleType, Callable[[], RuleType]]
         , once=False
         , start_immediate=False
         ) -> loop_forever:
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
    :param bool start_immediate: if True, start rule immediate
    :return: asyncio.Task: can be cancelled later
    """
    from .utils.condition_any import ConditionAny

    if isinstance(cond, TimeTracker):
        once=True

    def deco(foo) -> loop_forever:
        assert asyncio.iscoroutinefunction(foo), f'Rule can decorate only async functions'
        @loop_forever(
                start_immediate=start_immediate
                , once=once
                , self_forward=True
                , comment=f'Rule for {cond}'
        )
        async def wrap(loop: loop_forever):
            _cond = await get_awaitable(cond, loop)
            if not loop.started.is_set():
                loop.started.set()
            if isinstance(_cond, (asyncio.Condition, ConditionAny)):
                async with _cond:
                    await _cond.wait()
                    await foo()
            else:
                await _cond
                await foo()
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
