from smarthome import _T, Thing
from typing import List, Callable, Dict, Generic
from logging import getLogger
import asyncio
from threading import Lock

logger = getLogger(__name__)

MODE_ASYNC = 1
MODE_SYNC = 2

class Binding(Generic[_T]):

    def __get__(self, instance, owner):
        self.app = instance
        return self

    def __set_name__(self, owner, name):
        self.name = name

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'{self.app}.{self.__class__.__name__}.{self.name}'

    def __new__(cls, *args, **kwargs):
        from ..app import App
        obj = object.__new__(cls)
        obj.subscribe_data: Dict[Thing, dict] = {}
        obj.data_lock = Lock()
        obj.data_que = asyncio.Queue()
        obj.sync_mode = MODE_ASYNC
        obj.app: App = None
        return obj

    def bind(self
             , push=True
             , subscribe=True
             , subscribe_data: dict = None
             , request = True
             , *args
             , thing: _T = None
             , **kwargs) -> _T:
        """
        Must return thing with new push-callback
        :param thing:
        :param push: whether to push data from thing
        :param subscribe: whether to subscribe thing to binding's updates
        :param request: whether to provide a thing a request callback
        :return:
        """
        assert thing is not None, f'{self}: thing should be provided'
        if isinstance(thing, (type, Callable)):
            thing = thing(*args, **kwargs)
        thing: Thing = thing
        if push:
            thing.push_callbacks.append(self.push)
        if subscribe:
            self.subscribe_data[thing] = subscribe_data
        if request:
            thing.request_callbacks.append(self.thing_request)
        thing: _T = thing
        logger.debug(f'{thing} binded to {self}')
        return thing

    def get_subscribed_thing(self, thing_id: str) -> Thing:
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
        logger.debug(f'update {thing} with {data}')
        await thing.async_update(data)

    async def thing_request(self, thing: Thing) -> dict:
        """
        Thing can request data update from binding, it should answer with data as a dict or None
        :param thing:
        :return:
        """
        raise NotImplementedError

    async def push(self, thing: Thing):
        raise NotImplementedError

    async def _start(self):
        if self.app is None:
            raise RuntimeError(f'could not start binding {self}, it is not yet connected to the app, please '
                               f'define it inside app class and istanciate the app')
        if asyncio.iscoroutinefunction(self.start):
            ret = await self.start() is True
            self.sync_mode = MODE_ASYNC
        else:
            ret = await self.app.async_run(self.start)
            self.sync_mode = MODE_SYNC
        if ret is True:
            logger.info(f'binding {self} started')
            return ret

    async def start(self) -> bool:
        """
        Can be async or usual sync-function. In case of usual function, ThreadPool will be used to mimic async-work
        When succesfull finish, must return True
        :return:
        """
        raise NotImplementedError
