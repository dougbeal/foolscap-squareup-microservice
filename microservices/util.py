import os
from functools import wraps
import json
from google.protobuf.json_format import ParseError

def create_requests_mock(op):
    from unittest.mock import patch
    from unittest.mock import Mock
    from unittest.mock import MagicMock
    import requests

    response = MagicMock(name='response')
    response.request = MagicMock(name='request')
    response.status_code = 200
    response.json.return_value = {
        "registrations": {
            "slug": "dryrun",
            "reference": "ti_r3fijdlkf"}
        }

    mock = MagicMock(spec=op, return_value=response, name='operation')

    return mock

logger = None

def flatten_item(item):
    # if hasattr(item, '__dict__'):
    #     return item.__dict__
    return str(item)

def log_struct_flatten(f):
    @wraps(f)
    def wrapper(*args, **kw):
        try:
            return f(*args, **kw)
        except google.protobuf.json_format.ParseError:
            struct = json.loads(json.dumps(args[0], default=flatten_item))
            return f(*[struct, *args[1:]], **kw)
    return wrapper

if os.getenv('GCP_PROJECT', ''):
    import google.cloud.logging
    from google.cloud import firestore

    # Instantiates a client
    logging_client = google.cloud.logging.Client()

    # Connects the logger to the root logging handler; by default this captures
    # all logs at INFO level and higher
    logging_client.setup_logging()
    logger = logging_client.logger(__name__)
    logger.log_struct = log_struct_flatten(logger.log_struct)
else:
    # must be imported after google.cloud.logging
    import logging
    import types
    from pprint import pformat
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


    def log_text(self, text, **kw):
        level = logging.INFO
        if 'severity' in kw:
            level = getattr(logging, kw.pop('severity'))
        self.log(level, text, **kw)

    logger.log_text = log_text.__get__(logger)
    def log_struct(self, info, **kw):
        logger.log_text(pformat(info), **kw)

    logger.log_struct = log_struct.__get__(logger)

    logger.log_text("local logging mode")
