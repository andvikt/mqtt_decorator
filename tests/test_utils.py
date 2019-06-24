from logging import basicConfig, DEBUG
basicConfig(level=DEBUG)
import smarthome.rules
from smarthome import utils, const
import pytest
import asyncio
import typing
from dataclasses import dataclass, field


def test_proxy():
    from smarthome.utils.proxy import LambdaProxy, proxy

    @dataclass()
    class TestObj:

        value: int = 1
        another_value: int = 4
        some_lambda: typing.Callable = field(default_factory=lambda: lambda: 20, compare=False)

        def property(self):
            return self.value + 2

        def __add__(self, other):
            return typing.cast(
                self.__class__
                , LambdaProxy(self, value = lambda x: x + other)
            )


    state = TestObj()
    state2 = TestObj()
    assert state == state2

    check1 = TestObj(value=4, another_value=9)

    mut = proxy(state
                , value=lambda x: x * 2
                , another_value = 9
                , some_lambda = lambda x: lambda : x() / 2
                )
    state.value += 1
    assert mut == check1
    assert ((state + 5) + 1).value == 8
    assert state.value == 2
    assert mut.value == 4
    assert state.some_lambda() == 20
    assert mut.some_lambda() == 10
    assert state.property() == 4
    assert mut.property() == 6
    assert mut.another_value == 9
    assert isinstance(mut, TestObj)
    assert isinstance(mut, LambdaProxy)

    mut_on_mut = LambdaProxy(mut, value=lambda x: x * 10)
    assert mut_on_mut.value == 40
    assert mut_on_mut.property() == 42

    test_dict = {'hello': mut}
    prox_dict = LambdaProxy(test_dict)

    assert prox_dict['hello'] is mut


@pytest.mark.asyncio
async def test_states():
    from smarthome import State, rule
    from asyncio_primitives import utils as async_utils
    st1 = State(False, _str='state1')
    st2 = State(False, _str='state2')
    hitcnt = 0

    @rule(st1 == st2)
    def hello():
        nonlocal hitcnt
        hitcnt+=1

    task = await hello()

    await st1.change(True)
    await st2.change(True)

    await st1.change(False)
    await st2.change(False)

    with async_utils.ignoreerror(asyncio.CancelledError):
        task.cancel()
        await task

    assert hitcnt == 2


@pytest.mark.asyncio
async def test_complex_rule():
    from smarthome import State, rule
    from asyncio_primitives import utils as async_utils
    st1 = State(0)
    st2 = State(0)
    hitcnt = 0

    @rule((st1 > st2) | (st2 < 2))
    async def comp_rule():
        nonlocal hitcnt
        hitcnt+=1
        const.logger.debug(f'new hit {hitcnt}')

    task = await comp_rule()

    await st2.change(1)
    await st2.change(2)
    await st1.change(3)
    assert hitcnt == 2

    with async_utils.ignoreerror(asyncio.CancelledError):
        task.cancel()
        await task

    @rule(((st1 + st2) == 2) | ((st2 - 1) == 5))
    async def add_rule():
        nonlocal hitcnt
        hitcnt += 1
        const.logger.debug(f'new hit {hitcnt}')


    task = await add_rule()
    await st1.change(1)
    await st2.change(1)
    await st2.change(6)

    assert hitcnt == 4
    with async_utils.ignoreerror(asyncio.CancelledError):
        task.cancel()
        await task

@pytest.mark.asyncio
async def test_max_count():

    counts = []

    @smarthome.rules.counter(max_count=3)
    async def hello(cnt):
        counts.append(cnt)
    await asyncio.gather(*[hello() for x in range(6)])

    assert counts == [0,1,2,0,1,2]

    @smarthome.rules.counter(max_wait=0.3)
    async def fast_count(cnt):
        counts.append(cnt)

    counts.clear()

    await fast_count()
    await asyncio.sleep(0.25)
    await fast_count()
    await asyncio.sleep(0.25)
    await fast_count()
    await asyncio.sleep(0.35)
    await fast_count()
    assert counts == [0,1,2,0]


@pytest.mark.asyncio
async def test_timeshed():
    from smarthome import rule, utils
    from datetime import timedelta
    started = utils.CustomTime.now()
    ended: utils.CustomTime = None

    @rule(utils.TimeTracker.now() + timedelta(seconds=0.5))
    async def hey():
        nonlocal ended
        ended = utils.CustomTime.now()

    await hey()
    await asyncio.sleep(1.2)
    assert round((ended - started).total_seconds()) == 1


@pytest.mark.asyncio
async def test_timeshed_multi():
    from smarthome import rule, utils
    from datetime import timedelta
    hitcnt = 0

    @utils.TimeTracker.repeat(time_interval=timedelta(seconds=0.3))
    async def hey(x, y):
        nonlocal hitcnt
        hitcnt+=1
        assert x == 1, y==2

    task = await hey(1, y=2)
    await asyncio.sleep(1)
    assert hitcnt == 3
    with pytest.raises(asyncio.CancelledError):
        task.cancel()
        await task

