import asyncio
import logging

import microservices.square.api as api




PRODUCTION = True
secrets = None
client = None

def set_webhook(level=logging.WARNING):
    logging.basicConfig(level=level)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(api.set_webhook(secrets=secrets, client=client))
    except:
        if not PRODUCTION:
            import pdb, traceback
            traceback.print_exc()
            pdb.post_mortem()    
    
def get_registrations(level=logging.WARNING):
    logging.basicConfig(level=level)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(api.get_registrations(secrets=secrets, client=client))
    except:
        if not PRODUCTION:        
            import pdb, traceback
            traceback.print_exc()
            pdb.post_mortem()

if __name__ == '__main__':
    PRODUCTION = False
    import fire
    import sys    
    from .. import development_config as config
    secrets = config.secrets
    client = config.SQUARE_CLIENT
    if not '--production' in sys.argv:
        from unittest.mock import patch
        from unittest.mock import Mock 
        from unittest.mock import MagicMock   

        @patch('requests.post', MagicMock(side_effect=Mock(status_code=200, json=lambda : {"data": {"id": "test"}}))) 
        @patch('requests.patch', MagicMock(side_effect=Mock(status_code=200, json=lambda : {"data": {"id": "test"}}))) 
        def mocked_function():
            fire.Fire()
        mocked_function()
    else:
        sys.argv.remove('--production')        
        fire.Fire()
