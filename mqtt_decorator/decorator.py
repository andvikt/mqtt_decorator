from paho.mqtt import client as mqtt
from functools import wraps, partial
import json
import yaml
from typing import MutableMapping, Pattern, Union, Callable, Any, Iterable, Match, Mapping, Tuple
import inspect
from logging import getLogger
import re

logger = getLogger('mqtt')

FIRST_ARGUMENT = '_fp'

mqtt.CONNACK

class Callback:

    def __init__(self, foo, parse_topic=False, parse_payload=False):
        self.foo = foo
        self.parse_topic = parse_topic
        self.parse_payload = parse_payload

    def __call__(self, *args, **kwargs):
        return self.foo(*args, **kwargs)


_key_type = Union[Pattern, str]


class Subscriptions(MutableMapping[_key_type, Tuple[Callback, Union[str, dict, Match]]]):

    def __init__(self):
        self._container = dict()

    def __setitem__(self, key: _key_type, value: Callback):
        self._container[key] = value

    def __getitem__(self, item):
        for _k, _c in self._container.items():
            if isinstance(_k, str) and _k == item:
                return _c, item
            elif isinstance(_k, Pattern) and _k.search(item):
                if _c.parse_topic:
                    return _c, _k.search(item).groupdict()
                else:
                    return _c, _k.search(item)
        raise KeyError(item)

    def __delitem__(self, key):
        self._container.__delitem__(key)

    def __iter__(self):
        return self._container.__iter__()

    def __len__(self):
        return self._container.__len__()


def regexp_parser(patt: Pattern):
    def parse(txt):
        return patt.search(txt).groupdict()
    return parse


def json_parser(txt):
    return json.loads(txt)


def yaml_parser(txt):
    return yaml.load(txt, yaml.FullLoader)


def parse_yml_or_json(txt):
    try:
        return yaml.load(txt)
    except:
        try:
            return json.loads(txt)
        except:
            logger.error(f'Could not parse json nor yml')
            return {'msg': txt}


class Client(mqtt.Client):

    def __init__(self, *args, qos=0, username=None, pwd=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_message = self.cb_wrap
        self.on_connect = self._on_connect
        self._subscriptions = Subscriptions()
        self._qos = qos

    def _on_connect(self, client: mqtt.Client, *args, **kwargs):
        logger.debug('connected')
        client.publish('/startup', 'OK')

    def cb_wrap(self, client, userdata, msg):
        logger.debug(f'msg arrived {msg}')
        cb, topic = self._subscriptions[msg.topic]
        if cb.parse_payload:
            data: dict = json.loads(msg.payload)
        else:
            data = msg.payload
        return cb(topic, data)

    def subscribe_handler(self
                          , topic
                          , qos=0
                          , parse_payload=None
                          , parse_topic=None):
        """
        Decorator. It adds a decorated foo to _subscriptions. When message arrives, it will be called with payload as
            data. If parse_json is True, json payload will be parsed as dict
        :param topic:
        :param qos:
        :param parse_payload:
        :return:
        """

        def decorate(foo):
            self._subscriptions[topic] = Callback(foo, parse_payload=parse_payload, parse_topic=parse_topic)
            return foo

        return decorate

import csv