from ..const import _T
from ..thing import Thing
from ..state import State
from ..utils.mixins import _MixLoops
from typing import List, Callable, Dict, Generic, DefaultDict, Tuple
from logging import getLogger
import asyncio
from threading import Lock
import queue
import warnings
from collections import defaultdict
import attr

logger = getLogger(__name__)

MODE_ASYNC = 1
MODE_SYNC = 2

class Binding(Generic[_T], _MixLoops):

    # if you want to protect binding from push after updates, set it to False
    eho_safe: bool = False

    def __set_name__(self, owner, name):
        self.name = name
        self._app = owner

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'{self.app}.{self.__class__.__name__}.{self.name}'

    def __new__(cls, *args, **kwargs):
        from ..app import App
        from .. import State
        obj = object.__new__(cls)
        obj.subscribe_data: Dict[Thing, dict] = {}
        obj.data_lock = Lock()
        obj.async_que = asyncio.Queue() # todo: add que managers for sync/async modes
        obj.thread_que = queue.Queue()
        obj.sync_mode = MODE_ASYNC
        #  subscriptions are asyncio.Condition, keys are thing_id, state_name
        obj.subscriptions: Dict[Tuple[str, str], State] = {}
        obj._app: App = None
        return obj

    @property
    def app(self):
        if self._app is None:
            raise RuntimeError('app is not set for')
        return self._app


    async def trigger_subscription(self, thing_id: str, state_name: str, value, is_command=False):
        logger.debug(f'Trigger {thing_id}.{state_name} = {value} from {self.name}')
        state = self.subscriptions.get((thing_id, state_name), None)
        if state is None:
            warnings.warn(f'{thing_id}.{state_name} is not found or not binded to {self.name}')
            return
        if is_command:
            await state.command(value, _from=self)
        else:
            await state.update(value, _from=self)

    def get_subscribed_thing(self, thing_id: str) -> Thing:
        warnings.warn('get_subscribed_thing', DeprecationWarning)
        for x in self.subscribe_data.keys():
            if x.unique_id == thing_id:
                return x
        logger.warning(f'Could not find {thing_id} in {self}')

    async def update_thing(self, thing: Thing, data: dict):
        """
        Bindings should use this method to update thing safely, thread-safe
        :param thing:
        :param data:
        :return:
        """
        warnings.warn('update_thing', DeprecationWarning)
        logger.debug(f'update {thing} with {data}')
        await thing.async_update(data, from_binding=self)

    async def thing_request(self, thing: Thing) -> dict:
        """
        Thing can request data update from binding, it should answer with data as a dict or None
        :param thing:
        :return:
        """
        raise NotImplementedError

    async def push(self, state: State, **data):
        raise NotImplementedError

    async def _start(self):
        if self.app is None:
            raise RuntimeError(f'could not start binding {self}, it is not yet connected to the app, please '
                               f'define it inside app class and istanciate the app')
        ret = await self.start_binding()
        if ret is True:
            self.loop_forever()(self._loop)
            await _MixLoops.start(self)
            logger.info(f'binding {self} started')
            return ret
        else:
            warnings.warn(f'{self.name} binding did not started')


    async def _loop(self):
        logger.debug(f'{self.name} binding has no loop')
        await asyncio.sleep(60 * 60 * 24)

    async def _stop(self):
        await _MixLoops.stop(self)
        await self.stop_binding()


    async def start_binding(self) -> bool:
        """
        Can be async or usual sync-function. In case of usual function, ThreadPool will be used to mimic async-work
        When succesfull finish, must return True
        :return:
        """
        raise NotImplementedError

    async def stop_binding(self):
        raise NotImplementedError
