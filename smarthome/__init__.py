import asyncio
import json
from typing import TypeVar
from copy import copy

_T = TypeVar('_T')

CHANGE = 'update'
COMMAND = 'command'

class state(object):

    def __init__(self, default=None):
        self.default = None
        self.name = None

    def __get__(self, instance, owner):
        return getattr(instance, f'_{self.name}')

    def __set_name__(self, owner, name):
        self.name = name
        self.owner: Thing = owner
        self.owner.states.append(name)
        setattr(owner, f'_{name}', self.default)

    def __set__(self, instance, value):
        old_value = self.__get__(instance, self.owner)
        if value == old_value:
            return
        setattr(instance, f'_{self.name}', value)
        asyncio.ensure_future(instance.push())


class ThingMeta(type):

    def __new__(cls, name, bases, args: dict):
        ret = type.__new__(cls, name, bases, args)
        states = copy(args.get('states', []))
        for x in bases:
            for x in getattr(x, 'states', []):
                if x not in states:
                    states.append(x)
        ret.states = states
        print(states)
        return ret


class Thing(object, metaclass=ThingMeta):

    root = ''

    def __set_name__(self, owner, name):
        self.name = name
        owner.things.append(name)

    async def push(self):
        raise NotImplementedError

    def as_dict(self):
        def wrap():
            for x in self.states:
                yield x, getattr(self, x)
        return dict(wrap())

    def as_json(self):
        return json.dumps(self.as_dict())

    def json_handler(self, json_raw: str):
        params: dict = json.loads(json_raw)
        for name, value in params.items():
            setattr(self, name, value)


def bind(thing: _T, push_call, *args, **kwargs) -> _T:

    class Binded(thing):

        async def push(self):
            return await push_call(self)

        def __repr__(self):
            return f'binded {thing} to {push_call}'

    return Binded(*args, **kwargs)


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


class App(object):
    things = []
