from smarthome import Thing, State
from . import utils


class Switch(Thing):
    root = 'switch'
    is_on = State(utils.str_to_bool, False)


class Dimmer(Thing):
    root = 'dimmer'
    dim_level = State(int, 0)


class Number(Thing):
    root = 'number'
    value = State(int, 0)


class String(Thing):
    root = 'string'
    value = State(str, '')


