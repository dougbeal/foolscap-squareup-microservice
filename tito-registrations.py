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

requests_cache.install_cache('tito', backend='sqlite', expire_after=300)


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

    json = r.json()
    log.debug(pformat(json))

    query = Root().child(Fields(name))
    find = query.find(json)[0]
    value = find.value
    log.debug(pformat(value))
    return value

async def get_registrations():
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/registrations"
    headers = {
        "Authorization": f"Token token={ACCESS_TOKEN}"
        }
    r = requests.get(url, headers=headers)

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


async def get_answers(question_slug):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/questions/{question_slug}/answers"
    headers = {
        "Authorization": f"Token token={ACCESS_TOKEN}"
        }
    r = requests.get(url, headers=headers)
    return r.json()

async def main():
    log = logging.getLogger(__name__)
    registrations, tickets, questions = await asyncio.gather( *map(asyncio.create_task, [get_tito_generic('registrations'), get_tito_generic('tickets'), get_questions()]) )

    for registration in registrations:
        log.debug(pformat(registration))        
        reg_tickets = []
        for ticket in tickets:
            log.debug(pformat(ticket))
            ticket_id = ticket['id']
            if registration['id'] == ticket['registration_id']:
                for question in questions:
                    slug = question['slug']
                    for answer in question['answers']:
                        log.debug(pformat(answer))
                        if answer['ticket_id'] == ticket_id:
                            ticket[slug] = answer['response']
                reg_tickets.append(ticket)
        registration['tickets'] = reg_tickets
    pprint(registrations)
    with open(__file__ + ".json", 'w') as output_file:
        json.dump(registrations, output_file)    # send forth
        
    #combine 
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
