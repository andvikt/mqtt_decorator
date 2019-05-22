from config import mqtt, Client
from smarthome.bindings.mqtt import MqttBinding
from smarthome import *
from threading import Thread
from threading import Lock
import re

mqtt_binding = MqttBinding(mqtt)

class MainApp(App):

    test_switch = Switch(bindings=[mqtt_binding])

app = MainApp()


def handle(client: Client, *args):
    print(args)

topic_parser = re.compile('/test/(?P<name>.*)')


def run_mqtt():
    mqtt_connected = Lock()
    mqtt_connected.acquire()

    def release(*args):
        mqtt_connected.release()

    mqtt.on_connect = release

    def target():
        mqtt.connect('m24.cloudmqtt.com', port=14884)
        mqtt.loop_forever()

    mqtt_thread = Thread(target=target)
    mqtt_thread.start()
    with mqtt_connected:
        print('mqtt connected')


async def main():
    run_mqtt()
    app.test_switch.is_on = True
    await asyncio.sleep(1)
    app.test_switch.is_on = False

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()

