import asyncio
import logging
from pprint import pformat

import microservices.tito.api as api

PRODUCTION = True
secrets = None


def set_webhooks(level=logging.WARNING):
    logging.basicConfig(level=level)


def sync(level=logging.WARNING):
    logging.basicConfig(level=level)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(api.sync(secrets))
    except:
        if not PRODUCTION:
            import pdb, traceback
            traceback.print_exc()
            pdb.post_mortem()


def get_registrations(level=logging.WARNING):
    logging.basicConfig(level=level)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(api.get_registrations(secrets))
    except:
        if not PRODUCTION:
            import pdb, traceback
            traceback.print_exc()
            pdb.post_mortem()            

def complete_tito_registrations(level=logging.WARNING):
    logging.basicConfig(level=level)

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    try:
        loop.run_until_complete(api.complete_tito_registrations(secrets))
    except:
        if not PRODUCTION:
            import pdb, traceback
            traceback.print_exc()
            pdb.post_mortem()

def complete_tito_registration(square_data={}, registration={}, registration_slug="", level=logging.DEBUG):
    logging.basicConfig(level=level)

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    try:
        loop.run_until_complete(api.complete_tito_registration(secrets, square_data=square_data, registration=registration, registration_slug=registration_slug))
    except:
        if not PRODUCTION:
            import pdb, traceback
            traceback.print_exc()
            pdb.post_mortem()            

def handle_exception(loop, context):
    if not PRODUCTION:
        log = logging.getLogger(__name__)
        # context["message"] will always be there; but context["exception"] may not
        msg = pformat(context)
        log.error(f"Caught exception: {msg}")



            
if __name__ == '__main__':
    PRODUCTION = False
    import fire
    from .. import development_config as config
    secrets = config.secrets
    fire.Fire()
