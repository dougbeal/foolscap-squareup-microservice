from functools import partial
from os import path
from pprint import pprint, pformat
import asyncio
import concurrent.futures
import json
import logging

from dateutil.parser import isoparse
from jsonpath_ng import jsonpath, Slice, Fields, Root
from jsonpath_ng.ext import parse
import requests
import requests_cache

from .. import storage




CONVENTION_YEAR = "2020"
FOOLSCAP = CONVENTION_YEAR
FOOLSCAP_MEMBERSHIP = "F20 Membership"

ACCOUNT_SLUG = "foolscap"
EVENT_SLUG = f"foolscap-{CONVENTION_YEAR}"

APIHOST = "https://api.tito.io"
APIVERSION = "v3"
APIBASE = f"{APIHOST}/{APIVERSION}"

def get_base_headers(secrets):
    access_token = secrets['metadata']['data']['tito']['production']['TITO_SECRET']

    return {
        "Authorization": f"Token token={access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
        }

def get_write_headers(secrets):
    base = get_base_headers(secrets)
    create_access_token = secrets['metadata']['data']['tito']['production']['TITO_SECRET']
    base["Authorization"] = f"Token token={create_access_token}"
    return base


async def get_tito_generic(secrets, name):
    log = logging.getLogger(__name__)
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/{name}"
    headers = get_base_headers(secrets)
    r = requests.get(url, headers=headers)

    if hasattr(r, 'from_cache'):
        if r.from_cache:
            log.info(f"request for {url} read from cache")

    json_result = r.json()
    log.debug(pformat(json_result))

    query = Root().child(Fields(name, 'data'))
    find = query.find(json_result)[0]
    value = find.value
    log.debug(pformat(value))
    return value

async def get_registrations(secrets):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/registrations"
    headers = get_base_headers(secrets)
    r = requests.get(url, headers=headers)

    json_result = r.json()
    log.debug(pformat(json_result))

    query = Root().child(Fields('registrations'))
    find = questions_query.find(json_result)[0]
    log.debug(pformat(questions_find))
    questions = questions_find.value
    log.debug(pformat(questions))

    return r.json()

async def get_tickets(secrets):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/tickets"
    headers = get_base_headers(secrets)
    r = requests.get(url, headers=headers)
    return r.json()

async def get_questions(secrets):
    log = logging.getLogger(__name__)
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/questions"
    headers = get_base_headers(secrets)
    result = requests.get(url, headers=headers)
    result_json = result.json()
    log.debug(pformat(result_json))
    futures = []

    questions_query = Root().child(Fields('questions'))
    questions_find = questions_query.find(result_json)[0]
    log.debug(pformat(questions_find))
    questions = questions_find.value
    log.debug(pformat(questions))

    # equivalent statement parse('questions[*].slug')
    question_slugs_query = questions_query.child(Slice()).child(Fields('slug'))
    question_slugs_find = question_slugs_query.find(result_json)
    question_slugs = [m.value for m in question_slugs_find]
    log.debug(pformat(question_slugs))

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = pool.map(get_answers, ( secrets for _ in question_slugs), question_slugs)
    for question, answer in list(zip(questions, await asyncio.gather(*futures))):
        question['answers'] = answer['answers']

    log.debug(pformat(questions))
    return questions


async def get_answers(secrets, question_slug):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/questions/{question_slug}/answers"
    headers = get_base_headers(secrets)
    response = requests.get(url, headers=headers)
    return response.json()

async def get_registrations(secrets):
    log = logging.getLogger(__name__)
    registrations, tickets, questions = await asyncio.gather( *map(asyncio.create_task, [get_tito_generic(secrets, 'registrations'), get_tito_generic(secrets, 'tickets'), get_questions(secrets)]) )

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
    log.debug(pformat(registrations))
    await storage.get_storage().write(__file__ + ".json", {'registrations': registrations})


async def create_tito_registration(secrets, data):
    log = logging.getLogger(__name__)
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/registrations"
    headers = get_write_headers(secrets)


    r = requests.post(url,
                      headers=headers,
                      json=data
                      )
    if r.status_code == 404 or r.status_code == 422:
        log.error(f"{r.status_code}: {url}, {headers}, {data}, {r} {r.text}")
        log.error(pformat(locals()))
    r.raise_for_status()
    log.info(f"{r.status_code}: url:{url}, headers:{headers}, data:{data}, r:{r} r.text{r.text}")
    json_result = r.json()
    log.debug(pformat(json_result))

    query = Root().child(Fields('registration'))
    find = query.find(json_result)[0]
    log.debug(pformat(find))

    return r.json()

# updated 2019-12-29
# INFO:__main__:tito releases: [
#  'Foolscap 2020 Membership - Early Bird',
#  'Bite of Foolscap Banquet',
#  'Foolscap 2020 Membership - Concom',
#  'Foolscap 2020 Membership',
#  'Foolscap 2020 Membership - Student or First Timer',
#  'Foolscap 2020 Membership - Dealer']
# INFO:__main__:square items: {
#  'F20 Banq - Regular',
#  "F20 Dealer's Space - Regular",
#  'F20 Membership - Early Bird',
#  'F20 Membership - Student/New'}
DEALER_MEMBERSHIP = { "F20 Dealer's Space - Regular", "F20 Dealer's Table - Regular" }

SQUARE_TITO_MAP = {
    'F20 Banq - Regular': 'Bite of Foolscap Banquet',
    "F20 Dealer's Space - Regular": 'Foolscap 2020 Membership - Dealer',
    "F20 Dealer's Table - Regular": 'Foolscap 2020 Membership - Dealer',
    'F20 Membership - Early Bird': 'Foolscap 2020 Membership - Early Bird',
    'F20 Membership - Student/New': 'Foolscap 2020 Membership - Student or First Timer',
    'F20 Membership - At con': 'Foolscap 2020 Membership'
    }

async def sync(secrets):
    log = logging.getLogger(__name__)
    json_files = [__file__.replace('tito', 'square') + '.json',
                  __file__ + ".json"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = pool.map(storage.get_storage().read, json_files)
    square_document, tito_document, releases = await asyncio.gather( *futures, get_tito_generic(secrets, 'releases') )

    tito_registrations = tito_document.to_dict().get('registrations')
    # square order_id is used as the source in tito to prevent duplicates
    query = Slice().child(Fields('source'))
    find = query.find(tito_registrations)
    tito_sources = {m.value for m in find}

    square = square_document.to_dict().get('registrations')
    log.info( "square fields " + pformat(list(square.items())[0]))
    log.info( "tito fields " + pformat(tito_registrations[0]))
    log.info( "tito releases fields " + pformat(releases[0]))

    tito_release_title_id = {}
    for release in releases:
        release_id = release['id']
        release_title = release['title']
        tito_release_title_id[release_title] = release_id



    square_by_date = sorted(list(square.items()), key=lambda tup: isoparse(tup[1]['closed_at']))

    order_from_square_tito_add = []
    order_from_square = []
    order_dates = {}
    for order_id, order in square_by_date:
        items = []
        tito = {'discount_code': ''}
        note = order.get('note', '')
        cust = order.get('customer', None)
        order_date = order['closed_at']

        email = ''
        name = ''
        if cust:
            email = cust.get('email_address', '')
            name = cust.get('given_name', '') + ' ' + cust.get('family_name', '')

        tito['name'] = name
        tito['email'] = email
        tito['source'] = order_id
        tito['line_items'] = []
        for line_item in order['line_items']:
            item_name = line_item['name']
            if 'variation_name' in line_item:
                item_name = item_name + " - " + line_item['variation_name']
            quantity = int(line_item['quantity'])
            tito_name = SQUARE_TITO_MAP[item_name]
            if item_name in DEALER_MEMBERSHIP: # two badger per dealer space
                quantity *= 2

            item = {
                'release_id': tito_release_title_id[tito_name],
                'quantity': quantity
                }
            tito['line_items'].append(item)
            for _ in range(int(quantity)):
                items.append(tito_name)
        if not tito['name']:
            tito['name'] = note.replace('\n', ' ')

        if not order_id in tito_sources:
            log.info(f"add to tito {tito} {order_date}")
            order_from_square_tito_add.append(tito)
        else:
            log.debug(f"already in tito {name} {email} {note}")

        tito = tito.copy()
        tito['order_date'] = order_date
        order_from_square.append(tito)
        order_dates[order_id] = order_date


    for order in tito_registrations:
        log.debug(order)




    log.info("square %i tito %i", len(square), len(tito_registrations))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = pool.map(create_tito_registration,
                           [secrets for _ in order_from_square_tito_add],
                           order_from_square_tito_add)

    results = await asyncio.gather(*futures)


    log.info("a result: %s", pformat(results[0]))
    log.debug("results: %s", pformat(results))

    # merge tito native and from square orders, sort by date made
    # sort tito by
    #  'completed_at': '2019-12-22T22:16:16.000-08:00',
    #  filter Source: None

    for reg in tito_registrations:
        if reg.get('source') is None:
            reg['order_date'] = reg['completed_at']
        else:
            order_date = order_dates[reg['source']]
            reg['order_date'] = reg['completed_at']

    sorted_by_date = sorted([*tito_registrations, *order_from_square], key=lambda item: isoparse(item['order_date']))
    log.info("sorted %s:", [order['name'] for order in sorted_by_date])

    query = Slice().child(Fields('item_name'))
    find = query.find(order_from_square)
    log.info("square items: %s", pformat({m.value for m in find}))
    log.info("tito releases: %s", pformat(tito_release_title_id))




# TODO: add paging for > 100 items
# TODO: webhook for new registations -> number memberships
