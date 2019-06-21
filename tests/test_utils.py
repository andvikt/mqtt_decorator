from logging import basicConfig, DEBUG
basicConfig(level=DEBUG)
import smarthome.rules
from smarthome import utils
from smarthome.utils.utils import loop_forever
import pytest
import asyncio


def test_proxy():
    from smarthome.utils.proxy import LambdaProxy, proxy
    class TestObj:
        value = 1
        another_value = 4

        def __init__(self):
            self.some_lambda = lambda: 20

        def property(self):
            return self.value + 2



    state = TestObj()
    mut = proxy(state
                , value=lambda x: x * 2
                , another_value = 'hello'
                , some_lambda = lambda x: lambda : x() / 2
                )
    state.value += 1
    assert state.value == 2
    assert mut.value == 4
    assert state.some_lambda() == 20
    assert mut.some_lambda() == 10
    assert state.property() == 4
    assert mut.property() == 6
    assert mut.another_value == 'hello'
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
    st1 = State(False)
    st2 = State(False)
    hitcnt = 0
    prox = st1 == st2
    @rule(prox)
    def hello():
        nonlocal hitcnt
        hitcnt+=1

    async with hello() as task:
        raise async_utils.Continue()

    await asyncio.sleep(0)
    await st1.change(True)
    await asyncio.sleep(0)
    await st2.change(True)
    # #
    # await st1.change(True)
    # await st2.change(True)

    task.cancel()
    assert hitcnt == 1

    @rule(((st1 <= 2) & (st2 >= 2)) | (st1 == 10))
    async def another_rule():
        nonlocal hitcnt
        hitcnt+=1

    async with another_rule() as task:
        pass
    #
    # await st1.change(0)
    # await st2.change(2)
    # await st1.change(10)
    #
    # assert hitcnt == 5

@pytest.mark.asyncio
async def test_task_cancel():

    started = False
    cancelled = False
    notreached = True

    async def hello():
        nonlocal started
        started = True
        await asyncio.sleep(10000)
        notreached = False

    def set_cancelled():
        nonlocal cancelled
        cancelled = True


    task = await utils.utils.wait_started(hello(), set_cancelled)
    await utils.utils.cancel_all()
    task.cancel()
    assert started and cancelled and notreached


@pytest.mark.asyncio
async def test_loop_forever():

    cnt = 0

    @loop_forever()
    async def hello():
        nonlocal cnt
        cnt+=1
        await asyncio.sleep(1)

    @loop_forever
    async def hello2():
        nonlocal cnt
        cnt += 1
        await asyncio.sleep(1)

    cancelled = False

    def set_cancelled():
        nonlocal cancelled
        cancelled = True

    @loop_forever(cancel_cb=set_cancelled)
    async def hello3():
        await asyncio.sleep(1)

    assert utils.utils.is_loop(hello)
    assert not utils.utils.is_loop(set_cancelled)

    await hello
    await hello2
    await hello3

    await asyncio.sleep(3)
    assert cnt == 6
    await utils.utils.cancel_all()
    assert cancelled==True


@pytest.fixture
async def cond():
    yield asyncio.Condition()


@pytest.fixture
async def rule_counter_max_count(cond):
    from smarthome.utils.utils import _is_rule
    @smarthome.rules.rule(cond)
    @smarthome.rules.counting(max_count=3)
    async def hello(cnt):
        print('hello', cnt)

    assert isinstance(hello, _is_rule)

    ret = await hello
    yield ret
    ret.cancel()


@pytest.fixture
async def rule_counter_max_wait(cond):
    from smarthome.utils.utils import _is_loop
    @smarthome.rules.rule(cond)
    @smarthome.rules.counting(max_wait=1)
    async def hello(cnt):
        print('hello', cnt)
    task = await hello
    assert isinstance(hello, _is_loop)
    yield hello
    task.cancel()

@pytest.mark.asyncio
async def test_rule_count(cond, rule_counter_max_count):
    for x in range(6):
        await asyncio.sleep(0)
        async with cond:
            cond.notify_all()


@pytest.mark.asyncio
async def test_rule_wait(cond, rule_counter_max_wait):
    for x in range(3):
        await asyncio.sleep(0)
        async with cond:
            cond.notify_all()
    await asyncio.sleep(2)
    for x in range(3):
        await asyncio.sleep(0)
        async with cond:
            cond.notify_all()

@pytest.mark.asyncio
async def test_timeshed():
    from smarthome import rule, utils
    from datetime import timedelta
    started = utils.CustomTime.now()
    ended: utils.CustomTime = None

    @rule(utils.TimeTracker.now() + timedelta(seconds=1))
    async def hey():
        nonlocal ended
        ended = utils.CustomTime.now()

    await hey
    await asyncio.sleep(3)
    assert round((ended - started).total_seconds()) == 1


@pytest.mark.asyncio
async def test_timeshed_multi():
    from smarthome import rule, utils
    from datetime import timedelta
    hitcnt = 0

    @rule(lambda: utils.TimeTracker.now() + timedelta(seconds=0.3))
    async def hey():
        nonlocal hitcnt
        hitcnt+=1

    await hey.start()
    await asyncio.sleep(1)
    assert hitcnt == 3
    await hey.stop()

@pytest.mark.asyncio
async def test_rule_state():
    from smarthome import rule, utils, State
    from datetime import timedelta

    state_1 = State(lambda x: x, False)
    state_2 = State(lambda x: x, False)

    triggered = asyncio.Event()
    hitcnt = 0
    data = 1

    @rule((state_1 == True) & (state_2 == True) & (lambda : data == 1))
    async def hey():
        nonlocal hitcnt
        triggered.set()
        hitcnt+=1

    await hey.start()
    await state_1.change(True)
    done, pend = await asyncio.wait([triggered.wait()], timeout=1)
    assert len(pend) > 0
    await state_2.change(True)
    done, pend = await asyncio.wait([triggered.wait()], timeout=1)
    assert len(done) == 1
    await utils.utils.cancel_all()


@pytest.mark.asyncio
async def test_rule_state2():
    from smarthome import rule, utils, State
    from datetime import timedelta

    state_1 = State(lambda x: x, False)
    state_2 = State(lambda x: x, False)

    triggered = asyncio.Event()
    hitcnt = 0

    @rule(
        (((state_1 >= 0) & (state_1 <= 2)) | ((state_1 > 4) & (state_1 < 6)))
        & (state_2 == True)
    )
    async def hey():
        nonlocal hitcnt
        triggered.set()
        hitcnt+=1

    await hey.start()
    await state_1.change(3)
    await state_2.change(True)
    done, pend = await asyncio.wait([triggered.wait()], timeout=1)
    assert len(pend) > 0
    await state_1.change(5)
    await triggered.wait()
    await hey.close()
    print(hitcnt)
    await utils.utils.cancel_all()


@pytest.mark.asyncio
async def test_rule_stat3():
    from smarthome import rule, utils, State
    from datetime import timedelta

    state_1 = State(lambda x: x, False)
    state_2 = State(lambda x: x, False)

    triggered = asyncio.Event()
    hitcnt = 0

    @rule(state_1 == state_2)
    async def hey():
        nonlocal hitcnt
        triggered.set()
        hitcnt+=1

    await hey
    await state_1.change('hello')
    await state_2.change(1)
    done, pend = await asyncio.wait([triggered.wait()], timeout=1)
    assert len(pend) > 0
    await state_2.change('hello')
    await triggered.wait()
    await utils.utils.cancel_all()

@pytest.mark.asyncio
async def test_rule_tracker():
    from smarthome import rule, utils

    cond1 = asyncio.Condition()
    cond2 = asyncio.Condition()
    triggered = 0

    @rule(utils.utils.track_conditions(cond1, cond2))
    async def hello():
        nonlocal triggered
        triggered+=1

    ret = await hello

    async with cond1:
        cond1.notify_all()

    await asyncio.sleep(0)

    async with cond2:
        cond2.notify_all()

    await asyncio.sleep(1)
    assert triggered == 2
    await utils.utils.cancel_all()

@pytest.mark.asyncio
async def test_rule_stat4():
    from smarthome import rule, utils, State
    from datetime import timedelta

    state_1 = State(lambda x: x, 0)
    state_2 = State(lambda x: x, 0)


    triggered = asyncio.Event()
    hitcnt = 0

    @rule((state_1 + state_2) == 2)
    async def hey():
        nonlocal hitcnt
        triggered.set()
        hitcnt+=1

    await hey
    await state_1.change(1)
    await state_2.change(1)
    await triggered.wait()
    await utils.utils.cancel_all()
