import asyncio
import logging

import microservices.square.api as api




PRODUCTION = True
secrets = None
client = None


def loop(api_function, level):
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(api_function(secrets=secrets, client=client))
    except:
        if not PRODUCTION:
            import pdb, traceback
            traceback.print_exc()
            pdb.post_mortem()

def set_webhook(level=logging.WARNING):
    return loop(api.set_webhook, level)

def get_membership_items(level=logging.WARNING):
    return loop(api.get_membership_items, level)

def get_registrations(level=logging.WARNING):
    return loop(api.get_registrations, level)


if __name__ == '__main__':
    PRODUCTION = False
    import fire
    import sys
    from .. import development_config as config
    secrets = config.secrets
    client = config.SQUARE_CLIENT
    dry_run = True
    if '--mode-production' in sys.argv:
        sys.argv.remove('--mode-production')
        #api.TITO_MODE = 'production'
        dry_run = False
    elif '--mode-production-dry-run' in sys.argv:
        sys.argv.remove('--mode-production-dry-run')
        #api.TITO_MODE = 'production'
        dry_run = True
    elif '--mode-test' in sys.argv:
        sys.argv.remove('--mode-test')
        #api.TITO_MODE = 'test'
        dry_run = False
    else:
        if '--mode-test-dry-run' in sys.argv:
            sys.argv.remove('--mode-test-dry-run')
        #api.TITO_MODE = 'test'
        dry_run = True

    if dry_run:
        print("running dry, with mocked requests.post, requests.patch, and requests.delete")
        #print("TITO_MODE " + api.TITO_MODE)
        from unittest.mock import patch
        from unittest.mock import Mock
        from unittest.mock import MagicMock

        @patch('requests.delete', MagicMock(side_effect=Mock(status_code=200, json=lambda : {"data": {"id": "test"}})))
        @patch('requests.post', MagicMock(side_effect=Mock(status_code=200, json=lambda : {"data": {"id": "test"}})))
        @patch('requests.patch', MagicMock(side_effect=Mock(status_code=200, json=lambda : {"data": {"id": "test"}})))
        def mocked_function():
            return fire.Fire()
        mocked_function()
    else:
        #print("TITO_MODE " + api.TITO_MODE)
        fire.Fire()
