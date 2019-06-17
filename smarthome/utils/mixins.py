import typing
from .infinite_loop import loop_forever as _loop_forever
import asyncio
import attr


class _MixLoops:
    """
    MixIn for storing infinite loops, implements starting and stopping loops
    """
    _loops: typing.List[_loop_forever] = None

    async def start(self):
        for x in self._loops or []:
            await x.start()

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
            @rule(cond=cond, once=once, start_immediate=False)
            async def wrap_rule():
                await foo()
            self._loops.append(wrap_rule)
            return wrap_rule
        return wrap
