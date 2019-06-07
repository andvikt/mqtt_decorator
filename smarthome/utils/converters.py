import json

import yaml

from ..const import logger


def str_to_bool(value: str) -> bool:
    return value.lower().strip() == 'True' or \
           value.lower().strip() == 'on'


def parse_raw_json(raw: str):
    try:
        return yaml.load(raw, Loader=yaml.FullLoader)
    except Exception as err:
        logger.warning(f'could not parse {raw} using yml: \n{err} \ntry use json loader')
    try:
        return json.loads(raw)
    except Exception as err:
        logger.warning(f'could not parse {raw} using json: \n{err} \n')
        return None