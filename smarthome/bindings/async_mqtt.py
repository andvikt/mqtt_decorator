from ..utils import parse_raw_json
from .binding import Binding
from typing import TypeVar, Pattern, Callable
from smarthome import Thing
from hbmqtt.client import MQTTClient
from hbmqtt.mqtt import constants as mqtt_const
from hbmqtt.session import ApplicationMessage
from logging import getLogger

import re
import asyncio
from dataclasses import dataclass

logger = getLogger('mqtt_binding')

_T = TypeVar('_T')

THING_ID = 'thing_id'

DEF_OUT_TOPIC = '/{app_name}/{thing_id}/out'
DEF_IN_TOPIC = '/{app_name}/{thing_id}/in'
DEF_SUBSCRIBE_TOPIC = '/{app_name}/+/in'

class MqttBinding(Binding):
    """
    MQTT Client runs in a separate thread, pushes recieved data to the main thread that processes it in async-fashion
    """
    eho_safe = True

    def __init__(self
                 , host: str
                 , port: int = None
                 , subscribe_topic=DEF_SUBSCRIBE_TOPIC
                 , in_topic: str = DEF_IN_TOPIC
                 , out_topic: str = DEF_OUT_TOPIC
                 , data_handler: Callable = None
                 , auth: str = None  #"usr:pass"
                 ):
        self.mqtt = MQTTClient()
        self.root_topic = subscribe_topic
        self.host=host
        self.port= f':{port}' if port else ''
        self.in_topic = in_topic
        self.out_topic = out_topic
        self.data_handler = data_handler
        self.data_lock = asyncio.Lock()
        self.auth = auth or ''
        self.loop_to_stop: asyncio.Future = None

    @property
    def parse_topic(self):
        return re.compile(self.in_topic.format(app_name = self.app.name, thing_id = rf'(?P<{THING_ID}>.*)'), re.IGNORECASE)

    @property
    def subs_topic(self):
        return self.root_topic.format(app_name = self.app.name)

    @property
    def subs_out_topic(self):
        return DEF_OUT_TOPIC.format(
            app_name=self.app.name
            , thing_id='+'
        )

    @property
    def uri(self):
        return f'mqtt://{self.auth}@{self.host}{self.port}'

    async def push(self, thing: Thing):
        logger.debug(f'push {thing}')
        await self.mqtt.publish(
            topic=DEF_OUT_TOPIC.format(app_name=self.app.name, thing_id=thing.unique_id)
            , message=thing.as_json().encode()
            , qos=2
            , retain=True
        )

    async def start(self):

        await self.mqtt.connect(self.uri)
        await self.mqtt.subscribe([(self.subs_topic, mqtt_const.QOS_0)])
        logger.debug(f'{self.name} connected and suscribed to {self.subs_topic}')

        async def loop():
            try:
                while True:
                    msg = await self.mqtt.deliver_message()
                    self.handle_msg(msg)
            except asyncio.CancelledError:
                pass

        self.loop_to_stop = asyncio.ensure_future(loop())

    def handle_msg(self, msg: ApplicationMessage):
        logger.debug(f'{self} handle {msg.topic}: {msg.data}')
        thing_id = self.parse_topic.match(msg.topic)
        if thing_id is not None:
            thing_id = thing_id.groupdict().get(THING_ID)
        if thing_id is None:
            logger.warning(f'{self} could not parse {msg.topic} using {self.parse_topic}')
            return
        logger.debug(f'{THING_ID}={thing_id}')
        thing = self.get_subscribed_thing(thing_id)
        if thing is None:
            return
        if self.data_handler is not None:
            data = self.data_handler(msg.data)
        else:
            data = parse_raw_json(msg.data)
        if data is not None:
            self.app.shedule_async_run(self.update_thing(thing, data))

    async def stop(self):
        self.loop_to_stop.cancel()
        try:
            while True:
                task: asyncio.Future = self.mqtt.client_tasks.pop()
                task.cancel()
        except IndexError as err:
            pass
        await self.mqtt.disconnect()
