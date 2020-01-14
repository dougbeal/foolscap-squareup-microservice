from pprint import pformat
import asyncio
import concurrent.futures
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
    #access_token = secrets['metadata']['data']['tito']['production']['TITO_SECRET']
    access_token = secrets['metadata']['data']['tito']['test']['TITO_SECRET']

    return {
        "Authorization": f"Token token={access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
        }

def get_write_headers(secrets):
    base = get_base_headers(secrets)
    #create_access_token = secrets['metadata']['data']['tito']['production']['TITO_SECRET']
    create_access_token = secrets['metadata']['data']['tito']['test']['TITO_SECRET']
    base["Authorization"] = f"Token token={create_access_token}"
    return base


def log_request(response):
    log = logging.getLogger(__name__)
    cache = ""
    if hasattr(response, 'from_cache'):
        if response.from_cache:
            cache = '[CACHE]'
    if response.status_code == 404 or response.status_code == 422:
        log.error("%s: %s %s %s\n\t"
                  "headers %s\n\t"
                  "json %s\n\t"
                  "resp %s\n\t"
                  "resp.headers %s\n\t"
                  "resp.text %s",
                  response.status_code, cache, response.request.method, response.request.url,
                  response.request.headers,
                  response.request.body,
                  response,
                  response.headers,
                  response.text
                  )
        log.error("locals %s", pformat(locals()))
    else:
        log.info("%s: %s %s %s\n\t",
                 response.status_code, cache, response.request.method, response.request.url)
        log.debug("headers %s\n\t"
                  "json %s\n\t"
                  "resp %s\n\t"
                  "resp.headers %s\n\t"
                  "resp.text %s",

                  response.request.headers,
                  response.request.body,
                  response,
                  response.headers,
                  response.text
                  )


async def get_tito_generic(secrets, name, params={}):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/{name}"
    headers = get_base_headers(secrets)
    resp = requests.get(url, headers=headers, params=params)
    log_request(resp)
    json_result = resp.json()
    return json_result

async def put_tito_generic(secrets, name, json, operation=requests.post):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/{name}"
    headers = get_write_headers(secrets)
    resp = operation(url, headers=headers, json=json)
    log_request(resp)
    resp.raise_for_status()
    json_result = resp.json()
    return json_result


async def get_answers(secrets, question_slug):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/questions/{question_slug}/answers"
    headers = get_base_headers(secrets)
    response = requests.get(url, headers=headers)
    return response.json()

async def get_registrations(secrets):
    registrations = await get_tito_generic(secrets, "registrations", params={ 'view': 'extended' })
    await storage.get_storage().write(__file__ + ".json", {'registrations': registrations})


async def create_tito_registration(secrets, registration, square_data):
    log = logging.getLogger(__name__)

    json_result = await put_tito_generic(secrets, 'registrations', json={'registration': registration})

    query = Fields('registration')
    find = query.find(json_result)[0]
    log.debug(pformat(find))

    registration_slug = find.value['slug']
    asyncio.create_task(put_tito_generic(secrets, f"registrations/{registration_slug}/confirmations", {}))
    asyncio.create_task(update_tito_tickets(secrets, json_result, square_data))

    return json_result


async def read_registrations():
    log = logging.getLogger(__name__)
    json_files = [__file__ + ".json",
                  __file__.replace('tito', 'square') + '.json']

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = pool.map(storage.get_storage().read, json_files)
    tito_document, square_document = await asyncio.gather(*futures)

    t, s = tito_document.get('registrations.registrations'), square_document.get('registrations')
    #log.debug("tito reg %s", pformat(t))
    #log.debug("square reg %s", pformat(s))
    return t,s

def square_registration_order_map(square_registrations):
    return square_registrations

# created registrations before confirming invice and update_tito_tickets, so this function goes back and does those
async def complete_tito_registrations(secrets):
    log = logging.getLogger(__name__)

    tito_registrations, square_registrations = await read_registrations()

    orders = square_registration_order_map(square_registrations)

    for registration in tito_registrations:
        #asyncio.create_task(put_tito_generic(secrets, f"registrations/{registration_slug}/confirmations", {}))
        #asyncio.create_task(update_tito_tickets(secrets, registration))
        square_data = orders.get(registration.get('source', None), {})
        asyncio.create_task(complete_tito_registration(secrets, square_data=square_data, registration=registration))

# created registrations before confirming invoice and update_tito_tickets, so this function goes back and does those
# does a single registration by slug
async def complete_tito_registration(secrets, square_data={}, registration={}, registration_slug=""):
    log = logging.getLogger(__name__)
    assert registration or registration_slug, "must be supplied with registration or registration_slug"
    # is supplied with registration slug, read data in
    if not registration and registration_slug:
        log.info("find tito reg slug %s", registration_slug)
        tito_registrations, square_registrations = await read_registrations()
        assert tito_registrations, "registrations must be loaded into storage"
        for reg in tito_registrations:
            if reg['slug'] == registration_slug:
                registration = reg
                break
        assert registration, "invalid registration_slug, no registration found"
        orders = square_registration_order_map(square_registrations)
        square_data = orders.get(registration.get('source', None), {})

    await asyncio.create_task(update_tito_tickets(secrets, registration, square_data))


async def update_tito_tickets(secrets, registration, square_data, badge_number=None):
    log = logging.getLogger(__name__)

    log.debug("tito reg %s", pformat(registration))
    log.debug("sqare dat %s", pformat(square_data))
    query = parse('$..note')
    match = query.find(square_data)
    notes = [m.value for m in match if m.value]
    log.debug("notes %s", pformat(notes))
    # came from square, try to determine Badge Name from registration_name
    # syntax
    # badge-name: Badge Alpha
    # email: alpha@foo.bar
    # badge-name: Badge Beta
    # email: beta@foo.bar
    query = parse("$..tickets[*]")
    match = query.find(registration)

    for num, ticket in enumerate([m.value for m in match]):

        log.debug("ticket %i %s", num, pformat(ticket))
        ticket_slug = ticket['slug']

        if not 'responses' in ticket:
            # need to load extended ticket
            log.debug("loading extended ticket {ticket_slug}")
            ticket = await get_tito_generic(secrets, f"tickets/{ticket_slug}")
        else:
            log.debug("ticket has responses")

        answers = ticket['responses']
        update = {}
        if registration['source']: # ticket came from square
            if not ticket['email'] and ticket['registration_email']:
                update['email'] = ticket['registration_email']
            if not ticket['first_name'] and ticket['registration_name']:
                update['first_name'] = ticket['registration_name'].split()[0]
            if not ticket['last_name'] and ticket['registration_name']:
                update['last_name'] = ' '.join(ticket['registration_name'].split()[1:])

            if not 'badge-name' in answers:
                badge_name = ticket.get('name', ticket['registration_name'])
                if num:
                    badge_name = f"{badge_name} {num}"
                if badge_name:
                    #update.setdefault('answers',[]).append({ 'slug': 'badge-name', 'primary_repsonse': badge_name })
                    update.setdefault('answers',{}).update({ 'badge-name': badge_name })


        if ticket['release_title'] != 'Bite of Foolscap Banquet' and not 'badge-number' in answers and badge_number:
            #update.setdefault('answers',[]).append({ 'slug': 'badge-number', 'primary_repsonse': badge_number })
            update.setdefault('answers', {}).update({ 'badge-number': str(badge_number) })

        if bool(update):
            update['release_id'] = ticket['release_id']
            log.info("update ticket[%s] %s", ticket['release_title'], pformat(update))
            #return asyncio.create_task(put_tito_generic(secrets, f"tickets/{ticket_slug}", update, operation=requests.patch))
            return await put_tito_generic(secrets, f"tickets/{ticket_slug}", {"ticket": update}, operation=requests.patch)
        else:
            log.debug("NOT update ticket[%s] %s", ticket['release_title'], pformat(update))
            return None



async def mark_tito_registration_paid(secrets, registration_slug):
    log = logging.getLogger(__name__)
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/registrations/{registration_slug}/confirmations"
    log.info(url)
    headers = get_write_headers(secrets)
    r = requests.post(url,
                      headers=headers
                      )
    if r.status_code == 404 or r.status_code == 422:
        log.error(f"{r.status_code}: {url}, {headers}, {r} {r.text}")
        log.error(pformat(locals()))
    r.raise_for_status()
    log.info(f"{r.status_code}: url:{url}, headers:{headers}, r:{r} r.text{r.text}")


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

    get_release_task = asyncio.create_task(get_tito_generic(secrets, 'releases'))
    tito_registrations, square_registrations = await read_registrations()
    # square order_id is used as the source in tito to prevent duplicates
    query = Slice().child(Fields('source'))
    find = query.find(tito_registrations)
    tito_sources = {m.value for m in find}

    log.info( "square fields " + pformat(list(square_registrations.items())[0]))
    log.info( "tito fields " + pformat(tito_registrations[0]))

    square_by_date = sorted(list(square_registrations.items()), key=lambda tup: isoparse(tup[1]['closed_at']))

    order_from_square_tito_add = []
    order_from_square = []
    order_dates = {}
    releases = {}
    for order_id, order in square_by_date:
        items = []
        tito = {'discount_code': ''}

        query = parse("$..note")
        match = query.find(order)
        note = [m.value for m in match]
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

            if not releases:
                releases = {}
                for item in get_release_task.result()['releases']:
                    releases[item['title']] = item['id']
                log.info("releases %s", pformat(releases))
            item = {
                'release_id': releases[tito_name],
                'quantity': quantity
                }
            tito['line_items'].append(item)
            for _ in range(int(quantity)):
                items.append(tito_name)
        if not tito['name']:
            tito['name'] = ' '.join(note)

        if not order_id in tito_sources:
            log.info(f"add to tito {tito} {order_date}")
            order_from_square_tito_add.append(tito)
        else:
            log.debug(f"already in tito {name} {email} {note}")

        tito = tito.copy()
        tito['order_date'] = order_date
        tito['note'] = note
        order_from_square.append(tito)
        order_dates[order_id] = order_date


    for order in tito_registrations:
        log.debug(order)




    log.info("square %i tito %i", len(square_registrations), len(tito_registrations))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = pool.map(create_tito_registration,
                           [secrets for _ in order_from_square_tito_add],
                           order_from_square_tito_add,
                           [square_registrations[item['source']] for item in order_from_square_tito_add])

    registration_creation_results = await asyncio.gather(*futures)


    # merge tito native and from square orders, sort by date made
    # sort tito by
    #  'completed_at': '2019-12-22T22:16:16.000-08:00',
    #  filter Source: None

    for reg in [*tito_registrations, *registration_creation_results]:
        if reg.get('source') is None:
            reg['order_date'] = reg['completed_at']
        else:
            reg['order_date'] = order_dates[reg['source']]
            reg['square_data'] = square_registrations[reg['source']]


    sorted_by_date = sorted([*tito_registrations, *registration_creation_results], key=lambda item: isoparse(item['order_date']))
    log.info("sorted %s:", [order['name'] for order in sorted_by_date])


    if not releases:
        releases = {}
        for item in get_release_task.result()['releases']:
            releases[item['title']] = item['id']
        log.info("releases %s", pformat(releases))

    # add badge numbers
    badge_number = 2 # 1 is reserved
    for registration in sorted_by_date:
        for ticket in registration['tickets']:
            if not ticket['release_title'] == 'Bite of Foolscap Banquet':
                asyncio.create_task(update_tito_tickets(secrets, registration, registration.get('square_data', {}), badge_number=badge_number))
                badge_number = badge_number + 1




# TODO: add paging for > 100 items
# TODO: webhook for new registations -> number memberships
# TODO: mark regs as paid
# TODO: fill out tickets
