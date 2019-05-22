from .. import *

from config import mqtt
from typing import TypeVar

_T = TypeVar('_T')


async def push(item: Thing):
    print('push new state', f'/{item.root}/{item.name}/push', item.as_json())
    mqtt.publish(f'/{item.root}/{item.name}/push', item.as_json())


def bind_mqtt(item: _T) -> _T:
    return bind(item, push)
