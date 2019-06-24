
import secrets
from smarthome.bindings import MqttBinding
from smarthome import utils, rule, Group, things
from smarthome.things import Switch
from datetime import timedelta
from smarthome.utils import Sun
from smarthome.bindings import MegaBinding, MegaInput

__name__ = 'hy'
__skiproot__ = True


HOST = '127.0.0.1'
PORT = 1883


mqtt_binding = MqttBinding(host=HOST, port=PORT)#, auth=f'{secrets.MQTT_USER}:{secrets.MQTT_PWD}'
mega = MegaBinding(host='192.168.0.14/sec/', port=8238, ow_port=31)

grp = Group()

hello_switch = Switch(grp)
other_switch = Switch(grp)
sun = Sun('moscow')

test_temp = things.Temperature(grp).bind_to(mega, addr='testaddr')
test_button = things.Button(grp).bind_to(mega, input = MegaInput(7, 1, 1, 1))
test_relay = things.Switch(grp).bind_to(mega, pin=11)
test_servo = things.Number(grp).bind_to(mega, dir_rel = 14, move_rel = 15, close_time = 120)
test_speed = things.Number(grp).bind_to(mega, pins = [22, 23, 24])

mqtt_binding.bind_to(grp)


@rule(hello_switch.is_on)
async def test_rule():
    if hello_switch.is_on.value:
        print('hello')
    else:
        print('by')


@rule(hello_switch.is_on)
async def cond_rule():
    print('onothertest')


@rule(utils.TimeTracker.now() + 1)
async def timetrack_rule():
    print('hello from timetrack')


@sun.rule_sunset(timedelta(minutes=5))
async def sunset_rule():
    print('hello from sunset')

