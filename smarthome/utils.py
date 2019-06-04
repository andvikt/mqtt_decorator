import json

import yaml
from logging import getLogger
from functools import wraps, partial
import asyncio
from typing import Callable, Dict, TypeVar, Any, Generator, Tuple, Union, cast
from dataclasses import field
import attr

logger = getLogger('smarthome')
_T = TypeVar('_T')
_X = TypeVar('_X')

_LOOPS = []

def parse_raw_json(raw: str):
    try:
        return yaml.load(raw, Loader=yaml.FullLoader)
    except Exception as err:
        logger.warning(f'could not parse {raw} using yml: \n{err} \ntry use json loader')
    try:
        return json.loads(raw)
    except Exception as err:
        logger.warning(f'could not parse {raw} using json: \n{err} \n')
        return None


def loop_forever(foo=None, *, start_immediate=False, **kwargs):
    """
    Wraps a foo in endless while True loop
    :param foo:
    :param start_immediate: if True, immediatly ensure_future, return Future object
    :return:
    """
    def deco(foo):
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
            except asyncio.CancelledError:
                pass
        if start_immediate:
            ftr =  asyncio.ensure_future(wrapper(**kwargs))
            _LOOPS.append(ftr)
            return ftr
        return wrapper
    return deco if foo is None else deco(foo)

def dict_in(dct: Dict[_X, _T], *_in: _X) -> Generator[Tuple[_X, _T], None, None]:
    for x, y in dct.items():
        if x in _in:
            yield x, y


def start_callback(foo):
    """
    Replace call to foo with wrapper
    When foo is called before name is recieved, then foo is sheduled to call on startup of Thing

    :param foo:
    :return:
    """

    @wraps(foo)
    def wrapper(self, *args, **kwargs):
        if self.name is None:
            self.start_callbacks.append(partial(foo, self, *args, **kwargs))
            return self
        else:
            return foo(self, *args, **kwargs)

    return wrapper


def str_to_bool(value: str) -> bool:
    return value.lower().strip() == 'True' or \
           value.lower().strip() == 'on'

def rule(cond: asyncio.Condition, wait_for=None):
    """
    Rule-decorator
    When foo is decorated with rule, it is sheduled to run in endless loop awating on event
        , each time event triggers
        , foo is called
    :param cond:
    :param wait_for: if passed, wait_for will be used instead of wait, wait_for will be passed to wait_for
    :return:
    """
    def deco(foo):
        @loop_forever(start_immediate=True)
        async def wrap():
            async with cond:
                if not wait_for:
                    await cond.wait()
                else:
                    await cond.wait_for(wait_for)
                await foo()
        return wrap
    return deco

from datetime import datetime

def counting(max_count = None, max_wait=None):
    """
    Decorator. Decorated foo is called each time cond is triggered.
    Also counting number of trigerred event is passed as first argument
    :param max_count: Max count, after that counter will be set to zero
    :param max_wait: Max wait between counts in seconds
    :return:
    """

    def deco(foo: Callable[[int], Any]):
        cnt = 0
        last_time = datetime.now()
        async def wrap():
            nonlocal cnt
            nonlocal last_time
            if max_wait:
                if (datetime.now() - last_time).seconds >= max_wait:
                    cnt = 0
            if max_count:
                if cnt>=max_count:
                    cnt = 0
            await foo(cnt)
            cnt += 1
            last_time = datetime.now()
        return wrap
    return deco

def state(default, converter=None):
    from . import State
    return cast(
        State,
        attr.ib(
            factory=partial(State, converter or float, default)
            , init=False
        )
    )

def stop_loops():
    for x in _LOOPS:
        x.cancel()