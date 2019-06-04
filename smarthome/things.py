from smarthome import Thing, State


class Switch(Thing):
    root = 'switch'
    is_on = State(False)


class Dimmer(Thing):
    root = 'dimmer'
    dim_level = State(0)


class Number(Thing):
    root = 'number'
    value = State(0)


class String(Thing):
    root = 'string'
    value = State('')


