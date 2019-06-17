from megad import Mega, Relay, Servo, SpeedSelect, OneWireBus
from .binding import Binding
from .. import things
from ..state import State
import warnings
from .. import const
from typing import Callable
import asyncio
from ..utils.mixins import _MixLoops

DEF_OW_UPDATE_INTERVAL = 60


class MegaBinding(Binding):

    def __init__(self, host, port, ow_port=None, ow_update_interval=DEF_OW_UPDATE_INTERVAL):
        self.mega = Mega(host)
        self.port = port
        self.devices = {}
        self.ow_bus: OneWireBus = OneWireBus(self.mega, ow_port)
        self.ow_update_interval = ow_update_interval

    def get_device(self, id, factory: Callable[[], const._T], *args, **kwargs) -> const._T:
        if id in self.devices:
            return self.devices[id]
        else:
            self.devices[id] = dev = factory(*args, **kwargs)
            return dev

    async def start(self) -> bool:

        # map callbacks
        for key, val in self.subscriptions.items():
            # for buttons
            if isinstance(val.thing, things.Button):
                _key = self.subscribe_data[key].get('input')
                if _key is None:
                    raise RuntimeError(f'{self.name} binding can not map a callback for button {key}'
                                       f', "input" keyword is not provided')

                @self.mega.map_callback_deco(_key)
                async def callback(*args):
                    async with val.changed:
                        val.changed.notify_all()

            # for temperatures
            elif isinstance(val.thing, things.Temperature):
                if self.ow_bus is None:
                    raise RuntimeError(f'Try to bind {key} to mega OneWire, but OneWire is not set, provide "ow_port" to binding')
                addr = self.subscribe_data[key].get('addr')
                if addr is None:
                    raise RuntimeError(f'{self.name} binding can not map a callback for temp {key}'
                                       f', "addr" keyword is not provided')

                @self.ow_bus.map_callback_deco(addr)
                async def callback(temp: float):
                    await val.update(value=temp, _from=self)

        # start inputs listener
        await self.mega.start_listen(port=self.port)

        # start 1-wire bus
        if self.ow_bus:
            @self.loop_forever()
            async def update_temp():
                await asyncio.sleep(self.ow_update_interval)
                await self.ow_bus.update()

            await update_temp.start()

        return True

    async def stop_binding(self):
        await self.mega.stop()

    async def push(self, state: State, **data):
        pin: int = data.get('pin')
        is_servo: bool = 'dir_rel' in data
        is_speed: bool = 'pins' in data
        _id = state.thing.unique_id
        if pin is None:
            warnings.warn(f'{self.name} binding recived push from {state.thing}, but no pin is provided')
            return
        if isinstance(state.thing, things.Switch):
            dev = self.get_device(_id, Relay, self.mega, port=pin)
            if state.value:
                await dev.turn_on()
            else:
                await dev.turn_off()
        elif isinstance(state.thing, things.Number) and is_servo:
            dev = self.get_device(_id, Servo, mega=self.mega, **data)
            await dev.set_value(float(state.value))
        elif isinstance(state.thing, things.Number) and is_speed:
            dev = self.get_device(_id, SpeedSelect, self.mega, data['pins'])
            await dev.set_value(int(state.value))
