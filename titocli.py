import asyncio
import fire
import logging

import microservices.tito




def run_set_webhooks(level=logging.WARNING):
    logging.basicConfig(level=level)


def run_sync(level=logging.WARNING):
    logging.basicConfig(level=level)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(microservices.tito.sync())
    except:
        import pdb, traceback
        traceback.print_exc()
        pdb.post_mortem()    

def run_get_registrations(level=logging.WARNING):
    logging.basicConfig(level=level)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(microservices.tito.get_registrations())
    except:
        import pdb, traceback
        traceback.print_exc()
        pdb.post_mortem()    


if __name__ == '__main__':
    fire.Fire()        
