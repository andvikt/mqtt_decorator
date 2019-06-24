from . import Binding
from ..state import State
from typing import TypeVar, Pattern, Callable
from hbmqtt.client import MQTTClient
from hbmqtt.mqtt import constants as mqtt_const
from hbmqtt.session import ApplicationMessage
from logging import getLogger
import warnings
import attr

import re
import asyncio
from dataclasses import dataclass
from asyncio_primitives import utils as autils

logger = getLogger('mqtt_binding')

_T = TypeVar('_T')

THING_ID = 'thing_id'
STATE_NAME = 'state_name'

DEF_OUT_TOPIC = '/{app_name}/{thing_id}/{state_name}/out'
SUBS_OUT_TOPIC = '/{app_name}/+/+/out'
DEF_IN_TOPIC = '/{app_name}/{thing_id}/{state_name}/in'
SUBS_IN_TOPIC = '/{app_name}/+/+/in'
DEF_SUBSCRIBE_TOPIC = '/{app_name}/+/+/in'

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
        self.mqtt = MQTTClient(client_id='mqtt_binding')
        self.root_topic = subscribe_topic
        self.host=host
        self.port= f':{port}' if port else ''
        self.in_topic = in_topic
        self.out_topic = out_topic
        self.data_handler = data_handler
        self.data_lock = asyncio.Lock()
        self.auth = auth or ''
        self.loop_to_stop: asyncio.Future = None
        self._parse_topic: Pattern = None
        super().__init__()

    @property
    def parse_topic(self):
        if self._parse_topic is None:
            self._parse_topic = re.compile(
                self.in_topic.format(
                    app_name = self.app.name
                    , thing_id = rf'(?P<{THING_ID}>.*)'
                    , state_name = rf'(?P<{STATE_NAME}>.*)'
                ), re.IGNORECASE)
        return self._parse_topic

    @property
    def subs_topic(self):
        return self.root_topic.format(app_name = self.app.name)

    @property
    def subs_out_topic(self):
        return SUBS_OUT_TOPIC.format(
            app_name=self.app.name
        )

    @property
    def uri(self):
        return f'mqtt://{self.auth}@{self.host}{self.port}'

    async def push(self, state: State, **data):
        logger.debug(f'push {state}')
        await self.mqtt.publish(
            topic=DEF_OUT_TOPIC.format(app_name=self.app.name, thing_id=state.thing.unique_id, state_name=state.name)
            , message=str(state.value).encode()
            , qos=mqtt_const.QOS_1
        )

    async def start_binding(self) -> bool:
        await self.mqtt.connect(self.uri)
        await self.mqtt.subscribe([(self.subs_topic, mqtt_const.QOS_1)])
        logger.debug(f'{self.name} connected and suscribed to {self.subs_topic}')
        self._tasks.append(await self._loop())
        return True

    @autils.endless_loop
    async def _loop(self):
        msg = await self.mqtt.deliver_message()
        await self.handle_msg(msg)

    async def handle_msg(self, msg: ApplicationMessage):
        logger.debug(f'{self} handle {msg.topic}: {msg.data}')
        match = self.parse_topic.match(msg.topic)
        if match is not None:
            thing_id = match.groupdict().get(THING_ID)
        else:
            warnings.warn(f'{self} could not parse {msg.topic}')
            return
        if thing_id is None:
            warnings.warn(f'{self} could not parse {msg.topic} using {self.parse_topic}')
            return
        state_name = match.groupdict().get(STATE_NAME)
        if state_name is None:
            warnings.warn(f'{msg.topic} does not contain {STATE_NAME}')
            return
        await self.trigger_subscription(thing_id, state_name, value=msg.data.decode())

    async def stop_binding(self):
        await self.mqtt.unsubscribe([self.subs_topic])
        try:
            while True:
                task: asyncio.Future = self.mqtt.client_tasks.pop()
                task.cancel()
        except IndexError as err:
            pass
        await self.mqtt.disconnect()
