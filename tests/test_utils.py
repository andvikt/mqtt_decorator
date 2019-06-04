from smarthome import utils
import pytest
import asyncio

@pytest.fixture
async def cond():
    yield asyncio.Condition()

@pytest.fixture
async def rule_counter_max_count(cond):

    @utils.rule(cond)
    @utils.counting(max_count=3)
    async def hello(cnt):
        print('hello', cnt)
    yield hello

@pytest.fixture
async def rule_counter_max_wait(cond):

    @utils.rule(cond)
    @utils.counting(max_wait=1)
    async def hello(cnt):
        print('hello', cnt)
    yield hello

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