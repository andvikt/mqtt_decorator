from smarthome import Thing, State
from . import utils
import attr

@attr.s
class Switch(Thing):
    root = 'switch'
    is_on: State = utils.state(False, converter=utils.str_to_bool)

@attr.s
class Dimmer(Thing):
    root = 'dimmer'
    dim_level: State = utils.state(0, int)

@attr.s
class Number(Thing):
    root = 'number'
    value: State = utils.state(0, int)

@attr.s
class String(Thing):
    root = 'string'
    value: State = utils.state(0, str)


