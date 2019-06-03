from pytest import fixture
from mqtt_decorator.decorator import Client
from logging import getLogger
import secrets
import asyncio


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
        mqtt_binding = MqttBinding(mqtt_push_client)
        test_switch = Switch().bind(mqtt_binding)

    app = MainApp()
    app.start()
    yield app
    app.stop()
    await asyncio.sleep(1)


def test_names(app):
    assert app.test_switch.name == 'test_switch'


@fixture
def mqtt_push_subscribe(app):
    mqtt = Client()
    mqtt.enable_logger(getLogger('mqtt'))
    mqtt.username_pw_set(username=secrets.MQTT_USER, password=secrets.MQTT_PWD)

    def on_connect(*args, **kwargs):
        mqtt.subscribe(app.mqtt_binding.subs_out_topic)



    return mqtt


def test_switch_on_off(app):
    app.test_switch.is_on = True