from ..utils import parse_raw_json
from .binding import Binding
from typing import TypeVar, Pattern, Callable
from smarthome import Thing
from mqtt_decorator.decorator import Client
from logging import getLogger
from threading import Lock, Thread
from queue import Queue

import re
import asyncio

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
                 , mqtt: Client
                 , subscribe_topic=DEF_SUBSCRIBE_TOPIC
                 , in_topic: str = DEF_IN_TOPIC
                 , out_topic: str = DEF_OUT_TOPIC
                 , data_handler: Callable = None
                 ):
        self.mqtt = mqtt
        self.root_topic = subscribe_topic
        self.in_topic = DEF_IN_TOPIC
        self.out_topic = DEF_OUT_TOPIC
        self.data_handler = data_handler
        self.data_lock = Lock()
        self.msg_que = Queue()

    @property
    def parse_topic(self):
        return re.compile(self.in_topic.format(app_name = self.app.name, thing_id = rf'(?P<{THING_ID}>.*)'), re.IGNORECASE)

    @property
    def subs_topic(self):
        return self.root_topic.format(app_name = self.app.name)

    def push(self, thing: Thing):
        logger.debug(f'push {thing}')
        self.mqtt.publish(DEF_OUT_TOPIC.format(app_name=self.app.name, thing_id=thing.unique_id), thing.as_json())

    def start(self):
        mqtt_connected = Lock()
        mqtt_connected.acquire()
        def release(*args):
            mqtt_connected.release()
            logger.info(f'mqtt connected, subscribe to {self.subs_topic}')
            self.mqtt.subscribe(self.subs_topic)

        def disconnect(*args):
            logger.warning('disconnected, try to reconnect')
            mqtt_connected.acquire()

        def start():
            self.mqtt.connect('m24.cloudmqtt.com', port=14884)
            self.mqtt.loop_forever()

        self.mqtt.on_connect = release
        self.mqtt.on_disconnect = disconnect
        self.mqtt.on_message = self.handle_msg

        # begin new thread
        mqtt_thread = Thread(target=start)
        mqtt_thread.start()
        with mqtt_connected:
            return True

    def handle_msg(self, *args, **kwargs):
        try:
            self._handle_msg(*args, **kwargs)
        except Exception as err:
            logger.error(str(err))
            raise

    def _handle_msg(self, client, userdata, msg, *args):
        logger.debug(f'{self} handle {msg}')
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
            data = self.data_handler(msg.payload)
        else:
            data = parse_raw_json(msg.payload)
        if data is not None:
            self.app.shedule_async_run(self.update_thing(thing, data))
