#%%
from config import mqtt
from smarthome.bindings.mqtt import MqttBinding
from smarthome.things import Switch
from smarthome.app import App
import asyncio


class MainApp(App):

    mqtt_binding = MqttBinding(mqtt)
    test_switch = Switch().bind(mqtt_binding)

app = MainApp()


async def main():
    await app._start()
    app.test_switch.is_on = True
    await app.test_switch.push()
    await asyncio.sleep(10)
    app.test_switch.is_on = False
    await app.test_switch.push()

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
