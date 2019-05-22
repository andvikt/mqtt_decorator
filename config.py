from logging import basicConfig, DEBUG, getLogger
basicConfig(level=DEBUG)

from mqtt_decorator.decorator import Client

mqtt = Client(username='yloomjxa', pwd='feUZ51v-h7u-')
mqtt.enable_logger(getLogger('mqtt'))
mqtt.username_pw_set(username='yloomjxa', password='feUZ51v-h7u-')