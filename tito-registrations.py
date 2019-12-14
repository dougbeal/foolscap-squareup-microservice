import asyncio
import concurrent.futures
from pprint import pprint
import logging
import requests
import requests_cache

from jsonpath_rw import jsonpath, parse

from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

config = None
with open("secrets.yaml", "r") as yaml_file:
    config = load(yaml_file, Loader=Loader)
    
ACCESS_TOKEN = config['TITO_LIVE_SECRET']

requests_cache.install_cache('tito', backend='sqlite', expire_after=300)


CONVENTION_YEAR = "2020"
FOOLSCAP = CONVENTION_YEAR
FOOLSCAP_MEMBERSHIP = "F20 Membership"

ACCOUNT_SLUG = "foolscap"
EVENT_SLUG = f"foolscap-{CONVENTION_YEAR}"

APIHOST = "https://api.tito.io/"
APIVERSION = "v3"
APIBASE = f"{APIHOST}/{APIVERSION}"

#####
# gather all variations of membership (ConCom, AtCon, ...)
async def get_registrations():
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/registrations"
    headers = {
        "Authorization": f"Token token={ACCESS_TOKEN}"
        }
    r = requests.get(url, headers=headers)
    return r.json()

async def main():
        reg_json = await get_registrations()
        pprint(reg_json)

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())


# TODO: switch over to jsonpath to make json access less fragil?
# TODO: write out json files as debugging/cache ? https://realpython.com/caching-external-api-requests/ [sqllite]
#   https://joblib.readthedocs.io/en/latest/generated/joblib.Memory.html (conlusion - doesn't work with async)
#   just set cache timeout and don't worry about it?
#   webhook trigger invalidates cache?
