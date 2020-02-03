import asyncio

import microservices.square.api
import microservices.tito.api
import microservices.tito.main


async def bootstrap(secrets, client):
    tasks = []
    tasks.append(asyncio.create_task(microservices.square.api.get_registrations(secrets, client)))
    tasks.append(asyncio.create_task(microservices.tito.api.get_registrations(secrets)))
    await asyncio.gather(*tasks)
    tasks.clear()
    tasks.append(asyncio.create_task(microservices.tito.api.sync_active(secrets)))
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    import logging
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

    def bootstrap_main(level=logging.DEBUG):
       loop(bootstrap, level)

    PRODUCTION = False
    import fire
    import sys
    import microservices.development_config as config
    secrets = config.secrets
    client = config.SQUARE_CLIENT
    dry_run = True
    if '--mode-production' in sys.argv:
        sys.argv.remove('--mode-production')
        microservices.tito.api.TITO_MODE = 'production'
        dry_run = False
    elif '--mode-production-dry-run' in sys.argv:
        sys.argv.remove('--mode-production-dry-run')
        microservices.tito.api.TITO_MODE = 'production'
        dry_run = True
    elif '--mode-test' in sys.argv:
        sys.argv.remove('--mode-test')
        microservices.tito.api.TITO_MODE = 'test'
        dry_run = False
    else:
        if '--mode-test-dry-run' in sys.argv:
            sys.argv.remove('--mode-test-dry-run')
        microservices.tito.api.TITO_MODE = 'test'
        dry_run = True
    if dry_run:
        print("running dry, with mocked requests.post, requests.patch, and requests.delete")
        print("TITO_MODE " + microservices.tito.api.TITO_MODE)

        from unittest.mock import patch
        from unittest.mock import Mock
        from unittest.mock import MagicMock
        requests_mock = microservices.tito.main.create_requests_mock()

        @patch('requests.delete', requests_mock)
        @patch('requests.post', requests_mock)
        @patch('requests.patch', requests_mock)
        @patch.multiple('microservices.tito.api.requests',
                        post=requests_mock,
                        delete=requests_mock,
                        patch=requests_mock)
        def mocked_function():
            return fire.Fire()
        mocked_function()
    else:
        fire.Fire()