import asyncio
import json
from typing import TypeVar
from logging import getLogger

_T = TypeVar('_T')
logger = getLogger(__name__)

CHANGE = 'update'
COMMAND = 'command'

class state(object):

    def __init__(self, default=None):
        self.default = None
        self.name = None
        self.push_callbacks = []

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, f'_{self.name}', None)

    def __set_name__(self, owner, name):
        self.name = name
        self.owner = owner

    def __set__(self, instance, value):
        old_value = self.__get__(instance, None)
        if value == old_value:
            return
        logger.debug(f'set {instance}.{self.name} to {value}')
        setattr(instance, f'_{self.name}', value)
        asyncio.ensure_future(instance.push())

    def __str__(self):
        return f'<state> {self.owner}.{self.name}'


class ThingMeta(type):

    def __new__(cls, name, bases, args: dict):
        ret = type.__new__(cls, name, bases, args)
        ret.push_callbacks = []
        return ret


class Thing(object, metaclass=ThingMeta):

    root = ''

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj.push_callbacks = []
        return obj

    def __init__(self, *, bindings: list=None):
        for x in (bindings or []):
            x(self)

    @classmethod
    def get_states(cls):
        return {
            n: x for n, x in cls.__dict__.items() if isinstance(x, state)
        }

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        return self

    async def push(self):
        logger.debug(f'{self} begin push')
        await asyncio.gather(*[
            x(self) for x in self.push_callbacks
        ])

    def validate_args(self, kwargs):
        assert set(kwargs.keys()).issubset(set(self.get_states().keys()))\
            , f'{self} dont have states: {set(kwargs.keys()) - set(self.get_states().keys())}'

    async def update(self, args_dict: dict):
        self.validate_args(args_dict)
        await self.before_update()
        for n, x in args_dict.items():
            setattr(self, n, x)
        await self.after_update()

    async def before_update(self):
        """
        When bindigs update thing, they also call this method before update
        :return:
        """
        pass

    async def after_update(self):
        """
        When bindigs update thing, they also call this method before update
        :return:
        """
        pass

    def as_json(self):
        return json.dumps(
            {n: getattr(self, n) for n in self.get_states().keys()}
        )

    def json_handler(self, json_raw: str):
        params: dict = json.loads(json_raw)
        for name, value in params.items():
            setattr(self, name, value)

    def __str__(self):
        return f'{self.__class__}.{self.name} with state:  {self.as_json()}'


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
