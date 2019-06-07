from logging import getLogger
from typing import TypeVar

logger = getLogger('smarthome')
_T = TypeVar('_T')
_X = TypeVar('_X')
_ThingT = TypeVar('_ThingT')
CHANGE = 'update'
COMMAND = 'command'