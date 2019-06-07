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



@patch('smarthome.utils.CustomTime.now', new=lambda : 0)
def test_mock():
    print(utils.CustomTime.now())