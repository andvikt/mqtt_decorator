from .binding import Binding
from typing import TypeVar
from smarthome import Thing
from mqtt_decorator.decorator import Client
from logging import getLogger

logger = getLogger('mqtt_binding')

_T = TypeVar('_T')


class MqttBinding(Binding):

    def __init__(self, mqtt: Client):
        self.mqtt = mqtt


    async def push(self, thing: Thing):
        logger.debug(f'push {thing}')
        self.mqtt.publish(f'/{thing.root}/{thing.name}/push', thing.as_json())
