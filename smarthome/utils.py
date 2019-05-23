import json

import yaml
from logging import getLogger

logger = getLogger('smarthome')


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