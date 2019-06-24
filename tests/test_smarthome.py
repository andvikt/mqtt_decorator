from logging import basicConfig, DEBUG, getLogger, INFO
basicConfig(level=DEBUG)
#getLogger('hbmqtt').setLevel(INFO)

from pytest import fixture, yield_fixture
import secrets
import asyncio
import pytest
from hbmqtt.client import MQTTClient
from hbmqtt.mqtt import constants as mqtt_const
from hbmqtt.session import ApplicationMessage
from hbmqtt.broker import Broker, _defaults
from smarthome.bindings import async_mqtt
from smarthome import utils
from smarthome.app import App
from copy import copy
from threading import Thread
from unittest.mock import patch
from asyncio_primitives import utils as autils
import yaml

HOST = '127.0.0.1'
PORT = 1883


@fixture(scope='module')
async def broker():
    config = copy(_defaults)
    with open('broker.yml') as f:
        config = yaml.load(f, yaml.FullLoader)
    brok = Broker(config)
    await brok.start()
    yield brok
    await brok.shutdown()


@yield_fixture(scope='module')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@fixture(scope='module')
async def mqtt_client(broker, conf):
    client = MQTTClient()
    res = await client.connect(f'mqtt://{HOST}:{PORT}')
    await client.subscribe([('#', mqtt_const.QOS_0)])
    recieved = []
    @autils.endless_loop
    async def handle():
        msg = await client.deliver_message()
        recieved.append((msg.topic, msg.data.decode()))
    task = await handle()
    yield client
    await asyncio.sleep(1)
    await client.disconnect()
    await utils.utils.cancel_tasks(task)
    await utils.utils.cancel_tasks(*client.client_tasks)
    return


@pytest.mark.asyncio
async def test_broker(mqtt_client):
    await mqtt_client.ping()
    await mqtt_client.publish('test_topic', 'hello'.encode())


@fixture(scope='module')
async def conf():
    import tests.conf as _conf
    yield _conf


@fixture(scope='module')
async def app_load(conf):
    app = await App.from_module('test_app', conf)
    yield app


@fixture(scope='module')
async def app(app_load, conf):

    app = app_load
    assert conf.mqtt_binding.app == app
    assert conf.hello_switch.app is app
    assert conf.hello_switch.is_on.thing is conf.hello_switch
    assert conf.hello_switch.is_on is not conf.other_switch.is_on
    await app.start()

    yield app
    #teardown
    await app.stop()


@pytest.mark.asyncio
async def test_names(app, conf):
    assert conf.hello_switch.name == 'hello_switch'
    assert conf.other_switch.name == 'other_switch'


