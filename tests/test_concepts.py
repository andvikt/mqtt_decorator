from logging import basicConfig, DEBUG
basicConfig(level=DEBUG)

from pytest import fixture
import pytest
import pytest
from smarthome import App, utils
import asyncio
import astral
from unittest.mock import patch
import typing
from functools import partial
import wrapt


from hbmqtt.broker import Broker, _defaults
from copy import copy

@fixture()
async def broker():
    config = copy(_defaults)
    config['listeners'] = {
        'default': {
            'max-connections': 1000
            , 'type': 'tcp'
        }
        , 'my-tcp-1': {
            'bind': '127.0.0.1:1883'
        }
    }
    brok = Broker(config)
    await brok.start()
    yield brok
    await brok.shutdown()


@pytest.mark.asyncio
async def test_brok(broker):
    print(broker)


def test_sun():
    from smarthome.utils import Sun
    print(Sun('moscow').sunset())


def test_chain():
    from itertools import chain
    print(list(chain()))



async def print_coro(*args):
    print(*args)



@pytest.mark.asyncio
async def test_yield_from():
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def hello1():
        print('hello1')
        yield
        print('end hello1')

    @asynccontextmanager
    async def hello2():
        async with hello1():
            print('hello2')
            yield
            print('end hello2')

    async with hello2():
        print('heyho')


@pytest.mark.asyncio
async def test_asyncmanager():
    from contextlib import AbstractAsyncContextManager
    cond = asyncio.Condition()
    assert isinstance(cond, AbstractAsyncContextManager)


@pytest.mark.asyncio
async def test_custom_condition():
    from contextlib import AbstractAsyncContextManager

    class AsyncContextCounter(AbstractAsyncContextManager):
        """
        Counts every enter to the context
        When exiting context, notify inbound Condition and decreasing counter
        """
        def __init__(self):
            self.cond = asyncio.Condition()
            self.inc_lock = asyncio.Lock()
            self.lck = asyncio.Lock()
            self.idx = 0

        async def acquire(self):
            async with self.inc_lock:
                async with self.lck:
                    self.idx+=1

        async def release(self):
            async with self.lck:
                self.idx-=1
            async with self.cond:
                self.cond.notify_all()
            await asyncio.sleep(0)

        async def __aenter__(self):
            await self.acquire()

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.release()

        async def wait(self, idx=0):
            async with self.inc_lock:
                async with self.cond:
                    await self.cond.wait_for(lambda : self.idx == idx)

    class CustomCondition(AbstractAsyncContextManager):
        """
        Condition with async notify_all method. When we wait for notifiyng, we end waiting only when all the
        subscribers of the condition returns from the context
        Context is a Queu, that can be used to add tasks
        """
        def __init__(self):
            self.counter = AsyncContextCounter()
            self.cond = asyncio.Condition()
            self.tasks = asyncio.Queue()
            self.lck = asyncio.Lock()

        async def __aenter__(self):
            await self.counter.acquire()
            return self.tasks

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            while True:
                try:
                    task = self.tasks.get_nowait()
                except asyncio.QueueEmpty:
                    break

                async def wrap():
                    async with self.cond:
                        await self.cond.wait()
                        await task
                    await self.counter.release()
                await utils.utils.wait_started(wrap())

        async def notify_all(self):
            async with self.cond:
                self.cond.notify_all()
            await self.counter.wait()
            await asyncio.sleep(0)

    count = CustomCondition()
    chck = []

    async def test(idx):
        nonlocal chck
        chck.append(idx)

    async def race(start):
        for x in range(4):
            async with count as que:
                await que.put(test(start + x))

    await asyncio.gather(*[race(j*4) for j in range(4)])

    await count.notify_all()
    assert chck == [0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15]


