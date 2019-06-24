from functools import partial, wraps
from typing import cast

import attr
from types import ModuleType


def conf(mod: ModuleType):
    """
    Mark module as conf. Needed for automatic conf loading from another modules
    :param mod:
    :return:
    """
    assert isinstance(mod, ModuleType)
    setattr(mod, '__isconf__', True)
    return mod


def state(default, converter=None):
    from .state import State
    ret = partial(State, converter or float, default)
    setattr(ret, '_state', True)
    return cast(
        State
        , ret
    )


def start_callback(foo):
    """
    Replace call to foo with wrapper
    When foo is called before name is recieved, then foo is sheduled to call on startup of Thing

    :param foo:
    :return:
    """

    @wraps(foo)
    def wrapper(self, *args, **kwargs):
        if self.name is None:
            self.start_callbacks.append(partial(foo, self, *args, **kwargs))
            return self
        else:
            return foo(self, *args, **kwargs)

    return wrapper