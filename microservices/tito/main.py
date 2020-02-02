import asyncio
import logging
from pprint import pformat

import microservices.tito.api as api

PRODUCTION = True
secrets = None

def loop(api_function, level):
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(api_function(secrets=secrets))
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
    return loop(api.get_webhooks, level)

def sync(level=logging.WARNING):
    logging.basicConfig(level=level)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(api.sync_active(secrets))

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

def handle_exception(loop, context):
    if not PRODUCTION:
        log = logging.getLogger(__name__)
        # context["message"] will always be there; but context["exception"] may not
        msg = pformat(context)
        log.error(f"Caught exception: {msg}")





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
        from unittest.mock import patch
        from unittest.mock import Mock
        from unittest.mock import MagicMock

        requests_mock = MagicMock()
        requests_mock.status_code = 200
        requests_mock.json.return_value = {
            "registrations": {"slug": "dryrun"}
            }
        @patch('requests.delete', requests_mock)
        @patch('requests.post', requests_mock)
        @patch('requests.patch', requests_mock)
        def mocked_function():
            return fire.Fire()
        mocked_function()
    else:
        print("TITO_MODE " + api.TITO_MODE)
        fire.Fire()
