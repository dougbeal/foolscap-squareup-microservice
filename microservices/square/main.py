import logging
from pprint import pprint

import microservices.util as util
import microservices.square.api as api




PRODUCTION = True
secrets = None
client = None


def loop(api_function, level, *args, **kwargs):
    print("logging {logging.getEffectiveLevel()}")
    return util.async_entry_point(api_function, level, secrets, client, *args, production=PRODUCTION, **kwargs)

def set_webhook(level=logging.WARNING):
    return loop(api.set_webhook, level)

def get_membership_items(level=logging.WARNING):
    return loop(api.get_membership_items, level)

def get_registrations(level=logging.WARNING):
    return loop(api.get_registrations, level)

def get_year(year, level=logging.WARNING):
    result = loop(api.get_membership_orders_for_foolscap, level, year)
    pprint(result)
    return result


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
