import json

import yaml
from logging import getLogger
from functools import wraps
import asyncio
from typing import Callable, Dict, TypeVar, Any, Generator, Tuple

logger = getLogger('smarthome')
_T = TypeVar('_T')
_X = TypeVar('_X')

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
            return asyncio.ensure_future(wrapper(**kwargs))
        return wrapper
    return deco if foo is None else deco(foo)

def dict_in(dct: Dict[_X, _T], *_in: _X) -> Generator[Tuple[_X, _T], None, None]:
    for x, y in dct.items():
        if x in _in:
            yield x, y