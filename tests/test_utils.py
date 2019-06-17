import smarthome.rules
from smarthome import utils
from smarthome.utils.utils import loop_forever
import pytest
import asyncio

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

    assert hasattr(hello2, '_is_loop')

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

    @smarthome.rules.rule(cond)
    @smarthome.rules.counting(max_count=3)
    async def hello(cnt):
        print('hello', cnt)
    yield hello
    smarthome.rules.stop_loops()

@pytest.fixture
async def rule_counter_max_wait(cond):

    @smarthome.rules.rule(cond)
    @smarthome.rules.counting(max_wait=1)
    async def hello(cnt):
        print('hello', cnt)
    yield hello
    smarthome.rules.stop_loops()

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

    await hey.start()
    await asyncio.sleep(1)
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
    await hey.close()

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
    await hey.close()


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

    await hey.started.wait()
    await state_1.change('hello')
    await state_2.change(1)
    done, pend = await asyncio.wait([triggered.wait()], timeout=1)
    assert len(pend) > 0
    await state_2.change('hello')
    await triggered.wait()
    await hey.close()


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

    await hey.started.wait()
    await state_1.change(1)
    await state_2.change(1)
    await triggered.wait()

