from pprint import pformat


import google.cloud.logging

# Instantiates a client
client = google.cloud.logging.Client()

# Connects the logger to the root logging handler; by default this captures
# all logs at INFO level and higher
client.setup_logging()

log = logging.getLogger()

def foolscap_square_webhook(request):
    log.info(pformat(request))

def foolscap_tito_webhook(request):
    log.info(pformat(request))
