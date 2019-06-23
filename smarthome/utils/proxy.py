import typing
from ..const import _T
from functools import partial
from inspect import signature, getsource
import wrapt

def proxy(wrapped: _T, **kwargs):

    return typing.cast(_T, LambdaProxy(wrapped, **kwargs))


class LambdaProxy(typing.Generic[_T]):
    """
    Object wrapper. Modificates objects arguments with lambda function or constant
    Pass argument modificators as kwargs on initialisation
    Note that properties now does not work as expected, they stay the same as in source object
    Exs:

    ```
    class TestObj:
        value = 1
        another_value = 4

        def property(self):
            return self.value + 2

    state = TestObj()
    mut = LambdaProxy(state, value=lambda x: x * 2, another_value = 'hello')
    state.value += 1
    assert state.value == 2
    assert mut.value == 4
    assert state.property() == 4
    assert mut.property() == 6
    assert mut.another_value == 'hello'
    assert isinstance(mut, TestObj)
    assert isinstance(mut, LambdaProxy)
    ```
    """
    __not_wrapped__ = ['__repr__', '_kwargs', '_wrapt', '__getattribute__', 'show_lambdas']

    def __init__(self, wrapped: _T, **kwargs):
        self._wrapt = wrapped
        self._kwargs = kwargs
        pass

    def __getattribute__(self, item):
        __not_wrapped__ = object.__getattribute__(self, '__not_wrapped__')
        if item in __not_wrapped__:
            return object.__getattribute__(self, item)
        kwargs: dict = self._kwargs
        obj: object = self._wrapt
        if item in kwargs:
            ret = kwargs[item]
            if isinstance(ret, typing.Callable):
                return ret(obj.__getattribute__(item))
            else:
                return ret
        else:
            try:
                ret = obj.__getattribute__(item)
                if isinstance(ret, typing.Callable) \
                        and not isinstance(ret, type) \
                        and getattr(ret, '__name__', None) != '<lambda>':
                    try:
                        sig = signature(ret)
                        if 'self' in sig.parameters:
                            return partial(ret, self)
                        ret = getattr(obj.__class__, item)
                        sig = signature(ret)
                        if 'self' in sig.parameters:
                            return partial(ret, self)
                    except AttributeError:
                        pass
                return ret
            except AttributeError:
                ret = getattr(obj.__class__, item)
                if isinstance(ret, typing.Callable):
                    return partial(ret, self)
                else:
                    return ret

    def __getitem__(self, item):
        return self._wrapt.__getitem__(item)

    def __setitem__(self, key, value):
        return self._wrapt.__setitem__(key, value)

    def __repr__(self):
        show_wraps = {
            name: f'{self._wrapt.__getattribute__(name)}->' \
                  f'{foo(self._wrapt.__getattribute__(name)) if isinstance(foo, typing.Callable) else foo}'
            for name, foo in self._kwargs.items()
        }
        return f'LambdaProxy <{self._wrapt}: {show_wraps}>'

    def show_lambdas(self):
        return {
            x: getsource(value) for x, value in self._kwargs.items() if isinstance(value, typing.Callable)
        }

    @property
    def __add__(self):
        return partial(self._wrapt.__class__.__add__, self)

    @property
    def __sub__(self):
        return partial(self._wrapt.__class__.__sub__, self)

    @property
    def __truediv__(self):
        return partial(self._wrapt.__class__.__truediv__, self)

    @property
    def __mul__(self):
        return partial(self._wrapt.__class__.__mul__, self)

    @property
    def __eq__(self):
        return partial(self._wrapt.__class__.__eq__, self)

    @property
    def __ne__(self):
        return partial(self._wrapt.__class__.__ne__, self)

    @property
    def __le__(self):
        return partial(self._wrapt.__class__.__le__, self)

    @property
    def __lt__(self):
        return partial(self._wrapt.__class__.__lt__, self)

    @property
    def __ge__(self):
        return partial(self._wrapt.__class__.__ge__, self)

    @property
    def __gt__(self):
        return partial(self._wrapt.__class__.__gt__, self)

    @property
    def __and__(self):
        return partial(self._wrapt.__class__.__and__, self)

    @property
    def __or__(self):
        return partial(self._wrapt.__class__.__or__, self)
