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

HOST = 'm24.cloudmqtt.com'
PORT = 14884




@fixture()
async def mqtt_recieve(app):

    client = MQTTClient()
    await client.connect(f'mqtt://{secrets.MQTT_USER}:{secrets.MQTT_PWD}@{HOST}:{PORT}')
    await client.subscribe([
        (app.mqtt_binding.subs_out_topic, mqtt_const.QOS_0)
    ])
    yield client
    await client.disconnect()


@fixture
async def app():

    from smarthome.things import Switch
    from smarthome.app import App

    class MainApp(App):
        mqtt_binding = async_mqtt.MqttBinding(host=HOST, port=PORT, auth=f'{secrets.MQTT_USER}:{secrets.MQTT_PWD}')
        hello_switch = Switch().bind_to(mqtt_binding)

    app = MainApp()
    assert app.mqtt_binding.app == app
    assert app.hello_switch.app is app
    assert app.hello_switch.is_on.thing is app.hello_switch

    app.start()

    yield app

    await app.stop()
    await asyncio.sleep(1)


def test_names(app):
    assert app.hello_switch.name == 'test_switch'


@pytest.mark.asyncio
async def test_turn_on(app, mqtt_recieve):
    await app.started.wait()
    await app.hello_switch.is_on.command(True)
    msg: ApplicationMessage = await mqtt_recieve.deliver_message(timeout=5)
    assert msg.topic == async_mqtt.DEF_OUT_TOPIC.format(
        app_name=app.name
        , thing_id=app.hello_switch.unique_id
        , state_name=app.hello_switch.is_on.name
    )