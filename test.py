from mqtt_decorator.decorator import Client, parse_yml_or_json, regexp_parser
from logging import getLogger, basicConfig, DEBUG
import re
basicConfig(level=DEBUG)


mqtt = Client(username='yloomjxa', pwd='feUZ51v-h7u-')
mqtt.enable_logger(getLogger('mqtt'))
mqtt.username_pw_set(username='yloomjxa', password='feUZ51v-h7u-')




def handle(client: Client, *args, **kwargs):
    client.publish('dsdsd', 'afafaf')
    mqtt.subscribe('/#')
    print(*args, **kwargs)


mqtt.on_message = handle
mqtt.on_connect = handle

topic_parser = re.compile('/test/(?P<name>.*)')


# @mqtt.subscribe_handler('/test/#', parse_topic=regexp_parser(topic_parser), parse_payload=parse_yml_or_json)
# def hello(topic: dict, data: dict):
#     print(topic, data)

mqtt.connect('m24.cloudmqtt.com', port=14884)
mqtt.loop_forever()
