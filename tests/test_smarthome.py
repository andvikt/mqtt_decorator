from logging import basicConfig, DEBUG
#basicConfig(level=DEBUG)
from pytest import fixture
from mqtt_decorator.decorator import Client
from logging import getLogger
import secrets
import asyncio
from paho.mqtt import subscribe, client
import pytest
import threading
from smarthome.bindings.mqtt import DEF_OUT_TOPIC
import queue
from hbmqtt.client import MQTTClient
from hbmqtt.mqtt import constants as mqtt_const
from hbmqtt.session import ApplicationMessage

HOST = 'm24.cloudmqtt.com'
PORT = 14884




@fixture()
async def mqtt_recieve(app):

    client = MQTTClient()
    await client.connect(f'mqtt://{secrets.MQTT_USER}:{secrets.MQTT_PWD}@{HOST}:{PORT}')
    await client.subscribe([
        (app.mqtt_binding.subs_out_topic, mqtt_const.QOS_2)
    ])
    yield client
    await client.disconnect()


@fixture
def mqtt_push_client():
    mqtt = Client()
    mqtt.enable_logger(getLogger('mqtt'))
    mqtt.username_pw_set(username=secrets.MQTT_USER, password=secrets.MQTT_PWD)
    return mqtt


@fixture
async def app():
    from smarthome.bindings.async_mqtt import MqttBinding
    from smarthome.things import Switch
    from smarthome.app import App

    class MainApp(App):
        mqtt_binding = MqttBinding(host=HOST, port=PORT, auth=f'{secrets.MQTT_USER}:{secrets.MQTT_PWD}')
        test_switch = Switch().bind(mqtt_binding)

    app = MainApp()
    app.start()
    yield app
    await app.stop()
    await asyncio.sleep(1)


def test_names(app):
    assert app.test_switch.name == 'test_switch'


@pytest.mark.asyncio
async def test_turn_on(app, mqtt_recieve):
    await app.started.wait()
    app.test_switch.is_on = False
    await app.test_switch.push()
    msg: ApplicationMessage = await mqtt_recieve.deliver_message()
    print(msg.topic)