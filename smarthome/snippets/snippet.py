from ..things import Thing
from .. import things
from ..core import state, start_callback
from ..utils.converters import str_to_bool
from ..state import State
from ..rules import rule
from smarthome import loop_forever
import attr
import typing
import asyncio

@attr.s
class Snippet(Thing):
    """
    Snippet is actually a Thing, that combine some things inside and do some logic. It is like a dict, but implements
    its own logic and has its own states also
    """
    pass

IS_OFF = 0
IS_ON = 1
AUTO = 2
IDLE = 4
HEATING = 8
COOLING = 16

@attr.s
class Thermostat(Snippet):

    target_temp: things.Temperature = attr.ib(validator=attr.validators.instance_of(things.Temperature))
    current_temp: things.Temperature = attr.ib(validator=attr.validators.instance_of(things.Temperature))
    gistersis: things.Number = attr.ib(validator=attr.validators.instance_of(things.Number))

    heater: typing.Union[typing.Callable, Thing] = attr.ib(default=None)
    cooler: typing.Union[typing.Callable, Thing] = attr.ib(default=None)

    # if heater/cooler are Numbers, use this to iterate new values
    min_number: float = attr.ib(default=0)
    max_number: float = attr.ib(default=1)
    step: float = attr.ib(default=0.01)
    wait_time: float = attr.ib(default=30)

    cancel_task: typing.Awaitable = None

    is_on: State[bool] = state(False, str_to_bool)
    is_heating = False
    is_cooling = False

    async def heat(self):
        if not self.is_heating:
            self.is_heating = True
            self.is_cooling = False
            if self.cancel_task is not None:
                await self.cancel_task
                self.cancel_task = None
            if isinstance(self.heater, things.Switch):
                self.cancel_task = self.heater.is_on.command(False)
                return await self.heater.is_on.command(True)
            elif isinstance(self.heater, things.Number):
                htr = self.heater
                @loop_forever
                async def heat():
                    new_val = min([htr.value + self.step, self.max_number])
                    await htr.value.command(new_val)
                    await asyncio.sleep(self.wait_time)

                self.cancel_task = heat.close()

    async def cool(self):
        if not self.is_cooling:
            self.is_heating = False
            self.is_cooling = True
            if self.cancel_task is not None:
                await self.cancel_task
                self.cancel_task = None
            if isinstance(self.cooler, things.Switch):
                self.cancel_task = self.cooler.is_on.command(False)
                return await self.cooler.is_on.command(True)
            elif isinstance(self.cooler, things.Number):
                clr = self.cooler
                @loop_forever
                async def cool():
                    new_val = max([clr.value - self.step, self.min_number])
                    await clr.value.command(new_val)
                    await asyncio.sleep(self.wait_time)

                self.cancel_task = cool.close()

    async def stop_heat_cool(self):
        if self.is_heating or self.is_cooling:
            self.is_cooling = False
            self.is_heating = False
            if self.cancel_task is not None:
                await self.cancel_task
                self.cancel_task = None

    @property
    def current_state(self):
        if self.cooler.is_on:
            return 'cooling'
        if self.heater.is_on:
            return 'heating'


    def __attrs_post_init__(self):
        super().__attrs_post_init__()

        # heat when current temp is lower target-gistersis
        @self.rule((self.current_temp <= (self.target_temp.value - self.gistersis.value))
              & (self.is_on.value == True))
        async def heat():
            await self.heat()


        # stop heating or cooling when current temp is between current temp and gistersis
        @self.rule(
                ((self.current_temp > (self.target_temp.value - self.gistersis.value))
                  & (self.current_temp <= self.target_temp)
                  & (self.is_on.value == True))
                | (self.is_on.value == False)
              )
        async def stop():
            await self.stop_heat_cool()

        #cool when current temp is greater than target temp
        @self.rule((self.current_temp > self.target_temp)
              & (self.is_on.value == True))
        async def cool():
            await self.cool()
