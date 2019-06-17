from logging import basicConfig, DEBUG
basicConfig(level=DEBUG)
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

HOST = 'm24.cloudmqtt.com'
PORT = 14884



@fixture(scope='module')
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

@yield_fixture(scope='module')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@fixture(scope='module')
async def mqtt_client(conf):
    client = MQTTClient()
    await client.connect(f'mqtt://{secrets.MQTT_USER}:{secrets.MQTT_PWD}@{HOST}:{PORT}')
    await client.subscribe([
        (conf.mqtt_binding.subs_out_topic, mqtt_const.QOS_1)
    ])
    yield mqtt_client
    await client.disconnect()
    await asyncio.sleep(1)


@fixture(scope='module')
async def mqtt_recieve(app, conf, mqtt_client):
    client = mqtt_client
    lck = asyncio.Lock()
    recieved = []
    test = []
    async def collect_incoming():
        try:
            while True:
                msg: ApplicationMessage = await client.deliver_message(timeout=5)
                async with lck:
                    recieved.append((msg.topic, msg.data))
        except asyncio.CancelledError:
            pass

    async def add_to_test(topic, data):
        async with lck:
            test.append((topic, data))

    ftr = asyncio.ensure_future(collect_incoming())
    yield add_to_test
    #teardown
    await asyncio.sleep(1)
    ftr.cancel()
    assert test == recieved



@fixture(scope='module')
async def conf():
    import tests.conf as _conf
    yield _conf


@fixture(scope='module')
async def app_load(conf):
    app = App.from_module('test_app', conf)
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
    await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_names(app, conf):
    assert conf.hello_switch.name == 'hello_switch'
    assert conf.other_switch.name == 'other_switch'



@pytest.mark.asyncio
async def test_turn_on(app, conf, mqtt_recieve):
    await conf.hello_switch.is_on.command(True)
    await mqtt_recieve(async_mqtt.DEF_OUT_TOPIC.format(
        app_name=app.name
        , thing_id=conf.hello_switch.unique_id
        , state_name=conf.hello_switch.is_on.name
    ), str(True).encode())
    await asyncio.sleep(1)

@pytest.mark.asyncio
async def test_recieve_mqtt(app, conf, mqtt_client):
    await conf.hello_switch.is_on.command(True)
    await asyncio.sleep(1)
    async with conf.hello_switch.is_on.changed:
        await mqtt_client.publish(async_mqtt.DEF_IN_TOPIC.format(
            app_name=app.name
            , thing_id=conf.hello_switch.unique_id
            , state_name=conf.hello_switch.is_on.name
        )
            , str(False).encode()
            , qos=mqtt_const.QOS_1
        )
        await asyncio.wait([conf.hello_switch.is_on.changed.wait()], timeout=5.0)
        assert conf.hello_switch.is_on.value == False

@pytest.mark.asyncio
async def test_other_turn_on(app, conf, mqtt_recieve):
    await conf.other_switch.is_on.command(True)
    await asyncio.sleep(1)
    await mqtt_recieve(async_mqtt.DEF_OUT_TOPIC.format(
            app_name=app.name
            , thing_id=conf.other_switch.unique_id
            , state_name=conf.other_switch.is_on.name
        ), str(True).encode())

@pytest.mark.asyncio
async def test_parallel_sending(app, conf, mqtt_recieve):
    await asyncio.gather(
        test_turn_on(app, conf, mqtt_recieve)
        , test_other_turn_on(app, conf, mqtt_recieve)
    )