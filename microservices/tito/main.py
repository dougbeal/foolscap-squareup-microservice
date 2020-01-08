import asyncio
import logging

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


if __name__ == '__main__':
    PRODUCTION = False
    import fire
    from .. import development_config as config
    secrets = config.secrets
    fire.Fire()
