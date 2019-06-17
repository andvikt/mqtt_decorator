from logging import basicConfig, DEBUG
basicConfig(level=DEBUG)

from pytest import fixture
import pytest
import pytest
from smarthome import App, utils
import asyncio
import astral
from unittest.mock import patch


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


@pytest.mark.asyncio
async def test_task_cancel():

    async def hello():
        print('task started')
        try:
            await asyncio.sleep(10000)

        except asyncio.CancelledError:
            print('task cancelled')
            raise
        finally:
            print('task finished')

    async def rr():
        task = asyncio.create_task(hello())

        await asyncio.sleep(0)

        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            print('now cancelled')

    await rr()