from pprint import pformat
import os

if os.getenv('GAE_ENV', '').startswith('standard'):
    import google.cloud.logging
    from google.cloud import firestore

    # Instantiates a client
    client = google.cloud.logging.Client()

    # Connects the logger to the root logging handler; by default this captures
    # all logs at INFO level and higher
    client.setup_logging()

import logging
log = logging.getLogger()
 
def foolscap_square_webhook(request):
    log.info("%s %s", request, request.get_data())

def foolscap_tito_webhook(request):
    log.info("%s %s", request, request.get_data())
