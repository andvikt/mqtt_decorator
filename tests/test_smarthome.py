from logging import basicConfig, DEBUG
basicConfig(level=DEBUG)
from pytest import fixture
import secrets
import asyncio
import pytest
from hbmqtt.client import MQTTClient
from hbmqtt.mqtt import constants as mqtt_const
from hbmqtt.session import ApplicationMessage
from smarthome.bindings import async_mqtt
from smarthome import utils

HOST = 'm24.cloudmqtt.com'
PORT = 14884




@fixture(scope='module')
async def mqtt_recieve(app):

    client = MQTTClient()
    await client.connect(f'mqtt://{secrets.MQTT_USER}:{secrets.MQTT_PWD}@{HOST}:{PORT}')
    await client.subscribe([
        (app.mqtt_binding.subs_out_topic, mqtt_const.QOS_2)
    ])
    yield client
    #teardown
    await client.disconnect()
    await asyncio.sleep(1)


@fixture(scope='module')
async def app():

    from smarthome.things import Switch
    from smarthome.app import App

    class MainApp(App):
        mqtt_binding = async_mqtt.MqttBinding(host=HOST, port=PORT, auth=f'{secrets.MQTT_USER}:{secrets.MQTT_PWD}')
        hello_switch = Switch().bind_to(mqtt_binding)
        other_switch = Switch()

        def bind(self):
            self.other_switch.bind_to(self.mqtt_binding)

    app = MainApp()
    assert app.mqtt_binding.app == app
    assert app.hello_switch.app is app
    assert app.hello_switch.is_on.thing is app.hello_switch

    assert app.hello_switch.is_on is not app.other_switch.is_on

    await app.start()

    yield app
    #teardown
    await app.stop()



@pytest.mark.asyncio
async def test_names(app):
    assert app.hello_switch.name == 'hello_switch'
    assert app.other_switch.name == 'other_switch'



@pytest.mark.asyncio
async def test_turn_on(app, mqtt_recieve):
    await app.hello_switch.is_on.command(True)
    msg: ApplicationMessage = await mqtt_recieve.deliver_message(timeout=5)
    assert msg.topic == async_mqtt.DEF_OUT_TOPIC.format(
        app_name=app.name
        , thing_id=app.hello_switch.unique_id
        , state_name=app.hello_switch.is_on.name
    )

@pytest.mark.asyncio
async def test_recieve_mqtt(app, mqtt_recieve):
    await app.hello_switch.is_on.command(True)
    await asyncio.sleep(0)
    async with app.hello_switch.is_on.changed:
        await mqtt_recieve.publish(async_mqtt.DEF_IN_TOPIC.format(
            app_name=app.name
            , thing_id=app.hello_switch.unique_id
            , state_name=app.hello_switch.is_on.name
        )
            , str(False).encode()
            , qos=mqtt_const.QOS_2
        )
        await asyncio.wait([app.hello_switch.is_on.changed.wait()], timeout=5.0)
        assert app.hello_switch.is_on.value == False

@pytest.mark.asyncio
async def test_other_turn_on(app, mqtt_recieve):
    await app.other_switch.is_on.command(True)
    msg: ApplicationMessage = await mqtt_recieve.deliver_message(timeout=5)
    assert msg.topic == async_mqtt.DEF_OUT_TOPIC.format(
        app_name=app.name
        , thing_id=app.other_switch.unique_id
        , state_name=app.other_switch.is_on.name
    )

@pytest.mark.asyncio
async def test_parallel_sending(app, mqtt_recieve):
    await asyncio.gather(
        test_turn_on(app, mqtt_recieve)
        , test_other_turn_on(app, mqtt_recieve)
    )