import typing
import asyncio
from .utils import cancel_tasks
from ..rules import rule

class _MixRules(object):
    """
    MixIn for decorating inline functions as rules
    All defined rules are collected in _tasks argument and started/stopped using start/stop functions
    """
    def __init__(self):
        self._for_start: typing.List[typing.Callable] = []
        self._tasks: typing.List[asyncio.Task] = []

    async def start(self):
        if self._for_start:
            self._tasks.extend(await asyncio.gather(*self._for_start))

    async def stop(self):
        await cancel_tasks(*self._tasks)

    def rule(self, state):

        def deco(foo):
            self._for_start.append(rule(state)(foo)())
        return deco
