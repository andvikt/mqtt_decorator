from smarthome import _T, Thing


class Binding(object):

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj.subscribe_things = []
        return obj

    def __call__(self, thing: _T, push=True, subscribe=True, *args, **kwargs) -> _T:
        """
        Must return thing with new push-callback
        :param thing:
        :return:
        """
        if isinstance(thing, type):
            thing = thing(*args, **kwargs)
        thing: Thing = thing
        if push:
            thing.push_callbacks.append(self.push)
        if subscribe:
            self.subscribe_things.append(thing)
        thing: _T = thing
        return thing

    async def push(self, thing: Thing):
        raise NotImplementedError
