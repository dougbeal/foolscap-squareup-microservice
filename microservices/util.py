import os

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
if os.getenv('GCP_PROJECT', ''):
    import google.cloud.logging
    from google.cloud import firestore

    # Instantiates a client
    logging_client = google.cloud.logging.Client()

    # Connects the logger to the root logging handler; by default this captures
    # all logs at INFO level and higher
    logging_client.setup_logging()
    logger = logging_client.logger(__name__)
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
