from .core import state
from .utils.converters import str_to_bool
from .thing import Thing
from .state import State
import attr


class Switch(Thing):
    root = 'switch'
    is_on: State = state(False, converter=str_to_bool)


class Dimmer(Thing):
    root = 'dimmer'
    dim_level: State = state(0, int)


class Number(Thing):
    root = 'number'
    value: State = state(0, int)


class String(Thing):
    root = 'string'
    value: State = state(0, str)


class Button(Thing):
    root = 'button'
    value: State = state(0, int)


class Temperature(Thing):
    root = 'temp'
    value: State = state(0, float)
