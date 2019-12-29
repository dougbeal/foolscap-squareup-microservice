import asyncio
import concurrent.futures
from pprint import pprint, pformat
import logging
from functools import partial
import json

import requests
import requests_cache

from jsonpath_rw.jsonpath import *
from jsonpath_rw import parse

from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

config = None
with open("secrets.yaml", "r") as yaml_file:
    config = load(yaml_file, Loader=Loader)

ACCESS_TOKEN = config['TITO_LIVE_SECRET']


CONVENTION_YEAR = "2020"
FOOLSCAP = CONVENTION_YEAR
FOOLSCAP_MEMBERSHIP = "F20 Membership"

ACCOUNT_SLUG = "foolscap"
EVENT_SLUG = f"foolscap-{CONVENTION_YEAR}"

APIHOST = "https://api.tito.io/"
APIVERSION = "v3"
APIBASE = f"{APIHOST}/{APIVERSION}"

async def get_tito_generic(name):
    log = logging.getLogger(__name__)    
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/{name}"
    headers = {
        "Authorization": f"Token token={ACCESS_TOKEN}"
        }
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        log.error(f"404: {url}")    
    r.raise_for_status()

    json = r.json()
    log.debug(pformat(json))

    query = Root().child(Fields(name))
    find = query.find(json)[0]
    value = find.value
    log.debug(pformat(value))
    return value

async def add_registration(name, email, source, tickets):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/registrations"
    headers = {
        "Authorization": f"Token token={ACCESS_TOKEN}"
        }
    r = requests.post(url,
                      headers = headers,
                      data = {
#discount_code 	string 	The discount code used when registering.
# email 	string 	The email address of the registration.
# line_items 	array 	A list of LineItems for this registration: release_id and quantity. "line_items":[{"release_id":123,"quantity":1}
# name 	string 	The full name of the person who registered
# notify 	boolean 	Set this to true to send emails to the person registering and the organisers (if they have chosen to receive notifications). Default is false (no emails).
# source 	string 	The Source Tracking code that the person registered under.
                            }
                      )

    json = r.json()
    log.debug(pformat(json))

    query = Root().child(Fields('registrations'))
    find = questions_query.find(json)[0]
    log.debug(pformat(questions_find))    
    questions = questions_find.value
    log.debug(pformat(questions))
    
    return r.json()

async def get_tickets():
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/tickets"
    headers = {
        "Authorization": f"Token token={ACCESS_TOKEN}"
        }
    r = requests.get(url, headers=headers)
    return r.json()

async def get_questions():
    log = logging.getLogger(__name__)
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/questions"
    headers = {
        "Authorization": f"Token token={ACCESS_TOKEN}"
        }
    r = requests.get(url, headers=headers)
    json = r.json()
    log.debug(pformat(json))    
    futures = []

    questions_query = Root().child(Fields('questions'))
    questions_find = questions_query.find(json)[0]
    log.debug(pformat(questions_find))    
    questions = questions_find.value
    log.debug(pformat(questions))

    # equivalent statement parse('questions[*].slug')
    question_slugs_query = questions_query.child(Slice()).child(Fields('slug'))
    question_slugs_find = question_slugs_query.find(json)
    question_slugs = [m.value for m in question_slugs_find]
    log.debug(pformat(question_slugs))

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = pool.map(get_answers, question_slugs)
    for question, answer in list(zip(questions, await asyncio.gather(*futures))):
        question['answers'] = answer['answers']

    log.debug(pformat(questions))        
    return questions





async def aread_json(source):
    with open(source, 'r') as f:
        return json.load(f)

    
async def main():
    log = logging.getLogger(__name__)
    json_files = ['square-membership-orders.py.json', 'tito-registrations.py.json']

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = pool.map(aread_json, json_files)
        
    square, tito = await asyncio.gather( *futures )
    for order in square:
        note = order.get('note', '')
        cust = order.get('customer', None)
        name = ''
        if cust:
            email = cust.get('email', '')
            name = cust['given_name'] + ' ' + cust['family_name']
        log.debug(f"{name} {email} {note}")

        
    for order in tito:
        pprint(order)

    pprint(await get_tito_generic('releases'))


logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main())
except:
    import pdb, traceback
    traceback.print_exc()
    pdb.post_mortem()

# TODO: export data
# TODO: add paging for > 100 items
