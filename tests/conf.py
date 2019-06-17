
import secrets
from smarthome.bindings import MqttBinding
from smarthome import utils, rule
from smarthome.things import Switch
from smarthome import things
from datetime import timedelta
from smarthome.utils import Sun
from smarthome.bindings import MegaBinding, MegaInput

__name__ = 'hy'
__skiproot__ = True


HOST = 'm24.cloudmqtt.com'
PORT = 14884


mqtt_binding = MqttBinding(host=HOST, port=PORT, auth=f'{secrets.MQTT_USER}:{secrets.MQTT_PWD}')
mega = MegaBinding(host='192.168.0.14/sec/', port=8238, ow_port=31)

hello_switch = Switch().bind_to(mqtt_binding)
other_switch = Switch()
other_switch.bind_to(mqtt_binding)
sun = Sun('moscow')

test_temp = things.Temperature().bind_to(mega, addr='testaddr').bind_to(mqtt_binding)
test_button = things.Button().bind_to(mega, input = MegaInput(7, 1, 1, 1)).bind_to(mqtt_binding)
test_relay = things.Switch().bind_to(mega, port=11).bind_to(mqtt_binding)
test_servo = things.Number().bind_to(mega, dir_rel = 14, move_rel = 15, close_time = 120).bind_to(mqtt_binding)
test_speed = things.Number().bind_to(mega, pins = [22, 23, 24]).bind_to(mqtt_binding)


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

