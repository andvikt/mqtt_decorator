
import secrets
from smarthome.bindings import MqttBinding
from smarthome import utils, rule
from smarthome.things import Switch
from datetime import timedelta
from smarthome.utils import Sun

__name__ = 'hy'
__skiproot__ = True


HOST = 'm24.cloudmqtt.com'
PORT = 14884

mqtt_binding = MqttBinding(host=HOST, port=PORT, auth=f'{secrets.MQTT_USER}:{secrets.MQTT_PWD}')
hello_switch = Switch().bind_to(mqtt_binding)
other_switch = Switch()
other_switch.bind_to(mqtt_binding)
sun = Sun('moscow')


@rule(hello_switch.is_on.changed)
async def test_rule():
    if hello_switch.is_on.value:
        print('hello')
    else:
        print('by')


@rule(hello_switch.is_on.changed)
async def cond_rule():
    print('onothertest')


@rule(utils.TimeTracker.now() + 1)
async def timetrack_rule():
    print('hello from timetrack')


@rule(sun.sunset + 5)
async def sunset_rule():
    print('hello from sunset')
