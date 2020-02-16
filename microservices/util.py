import os
from functools import wraps
import json
import base64

from google.protobuf.json_format import ParseError

def create_requests_mock(op):
    from unittest.mock import MagicMock

    mock = MagicMock(**create_requests_mock_settings(op))
    return mock

def create_requests_mock_settings(op):
    from unittest.mock import patch
    from unittest.mock import Mock
    from unittest.mock import MagicMock
    import requests
    json_results = {
            "registrations": {
            "slug": "dryrun",
            "reference": "ti_r3fijdlkf"},
        "meta": {
            "total_pages": 1}
        }
    name = 'requests.op.'+op.__name__
    content = json.dumps(json_results).encode('ascii')
    mock_settings = {
        'autospec': op,
        'name': name,
        'return_value': MagicMock(autospec=requests.Response,
                                  **{
                                      'name': name + ".response",
                                      'request': MagicMock(autospec=requests.Request,
                                                           **{
                                                              'name': name + ".response.request",
                                                              }
                                                              ),
                                      'status_code': requests.codes.ok,
                                      'content': content,
                                      'encoding': 'ascii',
                                      'json.return_value': json_results,
                                      'text': json.dumps(json_results),
                                      },
                                  )
    }

    return mock_settings

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
