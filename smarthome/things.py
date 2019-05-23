from smarthome import Thing, state


class Switch(Thing):
    root = 'switch'
    is_on: bool = state(False)


class Dimmer(Thing):
    root = 'dimmer'
    dim_level: int = state(0)


class Number(Thing):
    root = 'number'
    value: float = state(0)


class String(Thing):
    root = 'string'
    value: str = state('')


