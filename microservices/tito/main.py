import asyncio
import logging
from pprint import pformat, pprint

import microservices.tito.api as api

PRODUCTION = True
secrets = None

def loop(api_function, level, *args, **kwargs):
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)

    loop = asyncio.get_event_loop()
    try:
        return loop.run_until_complete(api_function(secrets, *args, **kwargs))
    except:
        if not PRODUCTION:
            import pdb, traceback
            traceback.print_exc()
            pdb.post_mortem()

def create_update_webhook(level=logging.DEBUG):
    return loop(api.create_update_webhook, level)

def delete_all_webhooks(level=logging.DEBUG):
    return loop(api.delete_all_webhooks, level)

def get_webhooks(level=logging.DEBUG):
    pprint( loop(api.get_webhooks, level))

def sync(level=logging.WARNING):
    return loop(api.sync_active, level)

def get_registrations(level=logging.WARNING):
    return loop(api.get_registrations, level)

def dump_documents(level=logging.WARNING):
    logging.basicConfig(level=level)
    tito = {}
    square = {}
    j = ""
    try:
        j = asyncio.run(api.dump_documents())
    except:
        if not PRODUCTION:
            import pdb, traceback
            traceback.print_exc()
            pdb.post_mortem()
    return j

def void_tickets(event, references, level=logging.DEBUG):
    return loop(api.void_tickets, level, event, references)

def print_members(event, level=logging.WARNING):
    print(loop(api.print_members, level, event))

def cleanup_duplicates(level=logging.INFO):
    print(loop(api.cleanup_duplicates, level))

def handle_exception(loop, context):
    if not PRODUCTION:
        log = logging.getLogger(__name__)
        # context["message"] will always be there; but context["exception"] may not
        msg = pformat(context)
        log.error(f"Caught exception: {msg}")




def fire_mock():
    import fire
    import requests
    from unittest.mock import patch
    from unittest.mock import Mock
    from unittest.mock import MagicMock
    from microservices import create_requests_mock

    @patch('requests.delete', create_requests_mock(requests.delete))
    @patch('requests.post', create_requests_mock(requests.delete))
    @patch('requests.patch', create_requests_mock(requests.delete))
    def mocked_function():
        return fire.Fire()
    mocked_function()


if __name__ == '__main__':
    PRODUCTION = False
    import fire
    import sys
    from .. import development_config as config
    secrets = config.secrets
    # only one mode
    # --mode-test
    # --mode-test-dry-run
    #   default, reads from tito-test, mocks out writes
    # --mode-production
    # --mode-production-dry-run

    dry_run = True
    if '--mode-production' in sys.argv:
        sys.argv.remove('--mode-production')
        api.TITO_MODE = 'production'
        dry_run = False
    elif '--mode-production-dry-run' in sys.argv:
        sys.argv.remove('--mode-production-dry-run')
        api.TITO_MODE = 'production'
        dry_run = True
    elif '--mode-test' in sys.argv:
        sys.argv.remove('--mode-test')
        api.TITO_MODE = 'test'
        dry_run = False
    else:
        if '--mode-test-dry-run' in sys.argv:
            sys.argv.remove('--mode-test-dry-run')
        api.TITO_MODE = 'test'
        dry_run = True

    if dry_run:
        print("running dry, with mocked requests.post, requests.patch, and requests.delete")
        print("TITO_MODE " + api.TITO_MODE)
        fire_mock()
    else:
        print("TITO_MODE " + api.TITO_MODE)
        fire.Fire()
