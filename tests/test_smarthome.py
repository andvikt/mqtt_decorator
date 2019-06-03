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

HOST = 'm24.cloudmqtt.com'
PORT = 14884




@fixture()
def mqtt_recieve(app):

    class MqttThread(threading.Thread):

        def __init__(self):
            super().__init__(daemon=True)
            self.res: client.MQTTMessage = None
            self.and_queue = queue.Queue()

        def run(self) -> None:
            msg: client.MQTTMessage = subscribe.simple(
                topics=[app.mqtt_binding.subs_out_topic]
                , auth={'username': secrets.MQTT_USER, 'password': secrets.MQTT_PWD}
                , hostname=HOST
                , port=PORT
            )
            self.res = msg

    task = MqttThread()
    task.start()
    yield task

@fixture
def mqtt_push_client():
    mqtt = Client()
    mqtt.enable_logger(getLogger('mqtt'))
    mqtt.username_pw_set(username=secrets.MQTT_USER, password=secrets.MQTT_PWD)
    return mqtt


@fixture
async def app(mqtt_push_client):
    from smarthome.bindings.mqtt import MqttBinding
    from smarthome.things import Switch
    from smarthome.app import App

    class MainApp(App):
        mqtt_binding = MqttBinding(mqtt_push_client, host=HOST, port=PORT)
        test_switch = Switch().bind(mqtt_binding)

    app = MainApp()
    app.start()
    yield app
    app.stop()
    await asyncio.sleep(1)


def test_names(app):
    assert app.test_switch.name == 'test_switch'


@pytest.mark.asyncio
async def test_turn_on(app, mqtt_recieve):
    await app.started.wait()
    app.test_switch.is_on = False
    await app.test_switch.push()
    mqtt_recieve.join()
    assert mqtt_recieve.res.topic == DEF_OUT_TOPIC.format(
        app_name = app.name, thing_id = app.test_switch.unique_id
    )