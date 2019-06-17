import asyncio
import typing

import attr

from .mixins import _MixRules


@attr.s
class ConditionAny(_MixRules):
    """
    Mix multiple conditions into one, any of them triggers
    """
    conditions: typing.List[asyncio.Condition] = attr.ib()
    check: typing.Callable[[], bool] = attr.ib(default=None)
    cond: asyncio.Condition = attr.ib(factory=asyncio.Condition, init=False)

    async def __aenter__(self):
        await self.cond.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.cond.locked():
            self.cond.release()

    async def start(self):
        for x in self.conditions:
            @self.rule(x)
            async def trigger():
                async with self.cond:
                    check = True
                    if self.check is not None:
                        if asyncio.iscoroutinefunction(self.check):
                            check = await self.check()
                        else:
                            check = self.check()
                    if check:
                        self.cond.notify_all()
        await super().start()

    async def wait(self):
        if not self._loops:
            await self.start()
        await self.cond.wait()