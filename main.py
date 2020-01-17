from pprint import pformat

log = logging.getLogger()

def foolscap_square_webhook(request):
    log.debug(pformat(request))

def foolscap_tito_webhook(request):
    log.debug(pformat(request))
