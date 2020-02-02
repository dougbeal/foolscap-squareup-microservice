from pprint import pformat
import asyncio
import concurrent.futures
import logging
import json

from dateutil.parser import isoparse
from jsonpath_ng import jsonpath, Slice, Fields, Root
from jsonpath_ng.ext import parse
import requests
import requests_cache

from .. import storage
from .. import event_year



CONVENTION_YEAR = "2020"
FOOLSCAP = CONVENTION_YEAR
FOOLSCAP_MEMBERSHIP = "F20 Membership"

ACCOUNT_SLUG = "foolscap"
EVENT_SLUG = f"foolscap-{CONVENTION_YEAR}"

APIHOST = "https://api.tito.io"
APIVERSION = "v3"
APIBASE = f"{APIHOST}/{APIVERSION}"

TITO_MODE = 'test'

TITO_WEBHOOK_TRIGGERS = [#'ticket.created',
                        'registration.finished',
                         # 'registration.update',
                         # 'ticket.updated'
                         ]
def get_base_headers(secrets):
    access_token = secrets['metadata']['data']['tito'][TITO_MODE]['TITO_SECRET']
    return {
        "Authorization": f"Token token={access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
        }

def get_write_headers(secrets):
    base = get_base_headers(secrets)
    create_access_token = secrets['metadata']['data']['tito'][TITO_MODE]['TITO_SECRET']
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
        log.error("locals %s", locals())
    else:
        log.debug("%s: %s %s %s\n\t",
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


async def get_tito_generic(secrets, name, event=EVENT_SLUG, params={}):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{event}/{name}"
    headers = get_base_headers(secrets)
    resp = requests.get(url, headers=headers, params=params)
    log_request(resp)
    json_result = resp.json()
    return json_result

async def put_tito_generic(secrets, name, json=None, operation=None):
    if not operation:
        operation = requests.post
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/{name}"
    headers = get_write_headers(secrets)

    resp = None
    if json:
        resp = operation(url, headers=headers, json=json)
    else:
        resp = operation(url, headers=headers)

    log_request(resp)
    resp.raise_for_status()
    if resp.text:
        json_result = resp.json()
        return json_result
    return resp.text


async def read_registrations():
    log = logging.getLogger(__name__)
    st = storage.get_storage()
    services = ['tito', 'square']
    events = ['foolscap-2020', 'foolscap-2021']

    j = {}
    for service in services:
        for event in events:
            col = await st.get_event_collection_reference(service, event)
            (j.setdefault(st.col0, {}) # foolscap-microservices
             .setdefault(service, {}) # tito or square
             .setdefault(st.col1, {}) # events
             .setdefault(event, {})   # foolscap-2020
             )[st.col2] = collection_to_obj(col) # registrations

    return j

async def dump_documents():
    j = await read_registrations()

    with open('collections.dump.json', 'w', encoding='utf-8') as f:
        json.dump(j, f, ensure_ascii=False, indent=4)

    return j

def collection_to_obj(col):
    log = logging.getLogger(__name__)
    l = []
    for doc_snapshot in col.stream():
        obj = document_to_obj(doc_snapshot)
        l.append(obj)
    log.debug("collection[%s] of %i", col.parent, len(l))
    return l


def document_to_obj(doc_snapshot):
    log = logging.getLogger(__name__)

    obj = doc_snapshot.to_dict()
    log.debug("document %s %s", doc_snapshot.id, obj)
    return obj

async def write_tito_registration(j):
    log = logging.getLogger(__name__)
    log.info("storage reg %s", j.get('name'))
    event = EVENT_SLUG
    if 'event' in j:
        event = j['event']['slug']
    key = j['reference']
    service = 'tito'
    col = await storage.get_storage().get_event_collection_reference(service, event)
    document_reference = col.document(key)
    if not document_reference.get().exists:
        log.debug("writing reg %s", j)
        document_reference.create(j)
    else:
        log.debug("reg exists %s", j)


async def get_answers(secrets, question_slug):
    url = f"{APIBASE}/{ACCOUNT_SLUG}/{EVENT_SLUG}/questions/{question_slug}/answers"
    headers = get_base_headers(secrets)
    response = requests.get(url, headers=headers)
    return response.json()

async def get_registrations(secrets):
    log = logging.getLogger(__name__)
    resp = await get_tito_generic(secrets, "registrations", params={ 'view': 'extended' })

    registrations = resp['registrations']
    log.info("storing %i registrations", len(registrations))
    tasks = []
    # TODO: Batch firestore writes
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for reg in registrations:
            tasks.append(asyncio.create_task(write_tito_registration(reg)))
    await asyncio.gather(*tasks)
    return registrations


async def create_tito_registration(secrets, registration, square_data):
    log = logging.getLogger(__name__)

    json_result = await put_tito_generic(secrets, 'registrations', json={'registration': registration})

    query = Fields('registration')
    find = query.find(json_result)
    assert(len(find)>0)
    find = find[0]
    log.debug(find)

    registration_slug = find.value['slug']
    asyncio.create_task(put_tito_generic(secrets, f"registrations/{registration_slug}/confirmations", {}))
    asyncio.create_task(update_tito_tickets(secrets, json_result, square_data))

    return json_result



def square_registration_order_map(square_registrations):
    m = {}
    for reg in square_registrations:
        m[reg['order_id']] = reg
    return m

def is_membership_ticket(title):
    return not title in { 'Bite of Foolscap Banquet' }

async def update_tito_tickets(secrets, registration, square_data, badge_number=None):
    log = logging.getLogger(__name__)

    log.debug("tito reg %s", registration)
    log.debug("square data %s", square_data)
    query = parse('$..note')
    match = query.find(square_data)
    notes = [m.value for m in match if m.value]
    square_names = None
    # came from square, try to determine Badge Name from registration_name
    # syntax
    # badge-name: Badge Alpha
    # email: alpha@foo.bar
    # badge-name: Badge Beta
    # email: beta@foo.bar
    query = parse("$..tickets[*]")
    match = query.find(registration)
    registration_name = registration.get('name', "")
    bite_tickets = [m.value for m in match if not is_membership_ticket(m.value['release_title'])]
    # membership tickets
    membership_tickets = [m.value for m in match if is_membership_ticket(m.value['release_title'])]

    for num, ticket in enumerate(membership_tickets):
        log.debug("membership ticket ticket %i %s", num, ticket)
        ticket_slug = ticket['slug']

        if not 'responses' in ticket:
            # need to load extended ticket
            log.debug("loading extended ticket {ticket_slug}")
            ticket = await get_tito_generic(secrets, f"tickets/{ticket_slug}")
        else:
            log.debug("ticket has responses")

        answers = ticket['responses']
        update = {}

        # ticket came from square, unpack data from square customer and note
        if registration['source']:
            if not ticket['email'] and ticket['registration_email']:
                update['email'] = ticket['registration_email']
            if not ticket['first_name'] and ticket['registration_name']:
                update['first_name'] = ticket['registration_name'].split()[0]
            if not ticket['last_name'] and ticket['registration_name']:
                last_name = ' '.join(ticket['registration_name'].split()[1:])
                if last_name:
                    update['last_name'] = last_name

            if not 'badge-name' in answers:
                badge_name = ticket.get('name', ticket['registration_name'])
                if notes:
                    if not square_names:
                        square_names = notes[0].split('\n')

                    raw_badge_name = square_names.pop().split()
                    if len(raw_badge_name) > 2:
                        badge_name = ' '.join(raw_badge_name[0:2])
                    else:
                        badge_name = ' '.join(raw_badge_name)

                if badge_name:
                    #update.setdefault('answers',[]).append({ 'slug': 'badge-name', 'primary_repsonse': badge_name })
                    update.setdefault('answers',{}).update({ 'badge-name': badge_name })
            else:
                log.info("badge-name is already %s", answers)

        # assign badge number if not Bite and not already assigned
        if badge_number:
            ticket_badge_number = int(badge_number)+num

            if (not answers.get('badge-number') or
                answers.get('badge-number') and answers['badge-number'].isnumeric() and str(answers['badge-number']) != str(ticket_badge_number) ):
                #update.setdefault('answers',[]).append({ 'slug': 'badge-number', 'primary_repsonse': ticket_badge_number })
                log.info("badge-number will be updated to %s, answers: %s", ticket_badge_number, answers)
                # tito wants question answers to be strings
                update.setdefault('answers', {}).update({ 'badge-number': str(ticket_badge_number) })

        # If anything is set in update, send changes via tito update ticket
        if bool(update):
            log.info( "%s[%s]: %i membership tickets, %i non-membership tickets, notes %s",
                registration_name, badge_number,
                len(membership_tickets), len(bite_tickets),
                notes)                        
            update['release_id'] = ticket['release_id']
            log.info("update membership ticket[%s:%s] %s",
                     ticket_slug, ticket['release_title'],
                     update
                     )

            asyncio.create_task(put_tito_generic(secrets, f"tickets/{ticket_slug}", {'ticket':update}, operation=requests.patch))
            if len(bite_tickets):
                update = update.copy()
                bite = bite_tickets.pop()
                bite_ticket_slug = bite['slug']
                update['release_id'] = bite['release_id']
                log.info("update non-membership ticket[%s:%s] %s", bite_ticket_slug, ticket['release_title'], pformat(update))
                asyncio.create_task(put_tito_generic(secrets, f"tickets/{bite_ticket_slug}", {"ticket":update}, operation=requests.patch))
        else:
            log.debug("NOT update ticket[%s] %s", ticket['release_title'], pformat(update))




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
# DEALER_MEMBERSHIP = { "F20 Dealer's Space - Regular", "F20 Dealer's Table - Regular" }

# SQUARE_TITO_MAP = {
#     'F20 Banq - Regular': 'Bite of Foolscap Banquet',
#     "F20 Dealer's Space - Regular": 'Foolscap 2020 Membership - Dealer',
#     "F20 Dealer's Table - Regular": 'Foolscap 2020 Membership - Dealer',
#     'F20 Membership - Early Bird': 'Foolscap 2020 Membership - Early Bird',
#     'F20 Membership - Student/New': 'Foolscap 2020 Membership - Student or First Timer',
#     'F20 Membership - At con': 'Foolscap 2020 Membership',
#     'F20 Membership - Regular': 'Foolscap 2020 Membership'
#     }

# cache while function is resident    
TITO_RELEASE_NAMES = {}
TITO_RELEASE_NAME_ID = {}

async def get_tito_release_names(secrets, event):
    if not event in TITO_RELEASE_NAMES:
        log = logging.getLogger(__name__)
        resp = await get_tito_generic(secrets, "releases", event=event)
        query = parse('$.releases..title')
        match = query.find(resp)
        releases = [m.value for m in match]
        query = parse('$.releases..id')
        match = query.find(resp)
        rel_ids = [m.value for m in match]        
        log.info("tito %s releases %s", event, releases)
        TITO_RELEASE_NAMES[event] = releases
        TITO_RELEASE_NAME_ID[event] = dict(zip(releases, rel_ids))
    return TITO_RELEASE_NAMES[event], TITO_RELEASE_NAME_ID[event]

async def square_ticket_tito_name(secrets, event, name):
    tito_releases, _ = await get_tito_release_names(secrets, event)
    name_keywords = ['Banq', 'Dealer', 'Early', 'Student', 'Concom']
    for keyword in name_keywords:
        if keyword.lower() in name.lower():
            for tito in tito_releases:
                if keyword.lower() in tito.lower():
                    return tito
    if 'membership' in name.lower():
        # exclude keywords
        for keyword in name_keywords:
            tito_releases = [t for t in tito_releases if not keyword in t]
        return tito_releases[0]
    return None



async def sync_active(secrets):
    events = event_year.active()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = pool.map(sync_event,
                           [secrets for _ in events],
                           events)
    await asyncio.gather(*futures)
        
        

async def sync_event(secrets, event):
    log = logging.getLogger(__name__)
    log.info("syncing event %s", event)
    log.debug("reading registrations")
    j = await read_registrations()
    st = storage.get_storage()

    tito_registrations = j[st.col0]['tito'][st.col1][event][st.col2]
    square_registrations = j[st.col0]['square'][st.col1][event][st.col2]

    # TODO: filter out test or production tito entries

    # square order_id is used as the source in tito to prevent duplicates
    query = Slice().child(Fields('source'))
    find = query.find(tito_registrations)
    tito_sources = {m.value for m in find}

    if square_registrations:
        log.debug( "square fields " + pformat(square_registrations[0]))
    if tito_registrations:
        log.debug( "tito fields " + pformat(tito_registrations[0]))

    square_by_date = sorted(square_registrations, key=lambda reg: isoparse(reg['closed_at']))

    order_from_square_tito_add = []
    order_from_square = []
    order_dates = {}
    releases, rel_ids  = await get_tito_release_names(secrets, event)
    for order in square_by_date:
        order_id = order['order_id']
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

            tito_name = await square_ticket_tito_name(secrets, event, item_name)
            if not tito_name:
                log.warning("item %s not in map.", item_name)
                continue

            if 'dealer' in item_name.lower(): # two badger per dealer space
                quantity *= 2
                log.debug('%i dealer badges created', quantity)

            item = {
                'release_id': rel_ids[tito_name],
                'quantity': quantity
                }
            tito['line_items'].append(item)
            for _ in range(int(quantity)):
                items.append(tito_name)
        if not tito['name']:
            tito['name'] = ' '.join(note)

        # if there are no line_items, then its not a membership sale
        if tito['line_items'] and not order_id in tito_sources:
            log.info(f"add to tito {tito} {order_date}")
            order_from_square_tito_add.append(tito)
        else:
            log.debug(f"already in tito {name} {email} {note}")

        tito = tito.copy()
        tito['order_date'] = order_date
        tito['note'] = note
        order_from_square.append(tito)
        order_dates[order_id] = order_date


    log.info("reg count square %i tito %i.  creating %i",
             len(square_registrations),
             len(tito_registrations),
             len(order_from_square_tito_add)             
             )

    square_map = square_registration_order_map(square_registrations)    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = pool.map(create_tito_registration,
                           [secrets for _ in order_from_square_tito_add],
                           order_from_square_tito_add,
                           [square_map[item['source']] for item in order_from_square_tito_add])

    registration_creation_results = await asyncio.gather(*futures)
    new_tito_registrations = [r['registration'] for r in registration_creation_results if 'registration' in r]

    # merge tito native and from square orders, sort by date made
    # sort tito by
    #  'completed_at': '2019-12-22T22:16:16.000-08:00',
    #  filter Source: None


    log.debug("adding order_date for sorting")
    for reg in [*tito_registrations, *new_tito_registrations]:
        source = reg['source']        
        if source is None:
            reg['order_date'] = reg['completed_at']
        else:
            reg['order_date'] = order_dates[source]
            reg['square_data'] = square_map[source]


    sorted_by_date = sorted([*tito_registrations, *new_tito_registrations], key=lambda item: isoparse(item['order_date']))
    log.debug("sorted %s:", [order['name'] for order in sorted_by_date])


    # add badge numbers
    log.debug("adding badge numbers")
    badge_number = 2 # 1 is reserved
    tasks = []
    for registration in sorted_by_date:
        membership_count = len([ 0 for ticket in registration['tickets'] if not ticket['release_title'] == 'Bite of Foolscap Banquet'])
        tasks.append(asyncio.create_task(update_tito_tickets(secrets, registration, registration.get('square_data', {}), badge_number=badge_number)))
        badge_number = badge_number + membership_count

    # wait for everything to complete before sync is done
    log.debug("await tasks")
    await asyncio.gather(*tasks)
    log.debug("tasks done")


async def delete_all_webhooks(secrets):
    log = logging.getLogger(__name__)
    hooks = await get_webhooks(secrets)
    query = parse("$..id")
    match = query.find(hooks)
    webhook_ids = [m.value for m in match]
    log.info("webhook ids %s", webhook_ids)
    await asyncio.gather(*[asyncio.create_task(
        put_tito_generic(secrets,
                         "webhook_endpoints/" + str(whid),
                         operation=requests.delete
                         ))
                         for whid in webhook_ids])


async def get_webhooks(secrets):
    log = logging.getLogger(__name__)
    hooks = await get_tito_generic(secrets, 'webhook_endpoints')
    log.debug(hooks)
    return hooks

async def set_webhooks(secrets):
    data = {
        'webhook_endpoint':
        {
            'url': secrets['metadata']['data']['tito']['production']['WEBHOOK_URL'],
            'included_triggers': TITO_WEBHOOK_TRIGGERS
            }
        }
    return await put_tito_generic(secrets, 'webhook_endpoints', data)

async def update_webhook(secrets, webhook_ids):
    data = {
        'webhook_endpoint':
        {
            'url': secrets['metadata']['data']['tito']['production']['WEBHOOK_URL'],
            'included_triggers': TITO_WEBHOOK_TRIGGERS
            }
        }
    return await put_tito_generic(secrets, 'webhook_endpoints/' + str(webhook_ids), data, operation=requests.patch)

async def create_update_webhook(secrets):
    log = logging.getLogger(__name__)
    hooks = await get_webhooks(secrets)
    log.info("hooks %s", hooks)

    if len(hooks['webhook_endpoints']) > 1:
        log.info("more than one webhook, deleting all")
        await delete_all_webhooks(secrets)
        return await set_webhooks(secrets)
    elif len(hooks['webhook_endpoints']):
        triggers = hooks['webhook_endpoints'][0]['included_triggers']
        webhook_id = hooks['webhook_endpoints'][0]['id']
        if set(triggers).difference(set(TITO_WEBHOOK_TRIGGERS)):
            log.info("changes %s", set(triggers).difference(set(TITO_WEBHOOK_TRIGGERS)))
            log.info("need to update triggers %s:%s, %s:%s", type(triggers[0]), triggers, type(TITO_WEBHOOK_TRIGGERS[0]), TITO_WEBHOOK_TRIGGERS)
            log.info(triggers[0]==TITO_WEBHOOK_TRIGGERS[0])
            return await update_webhook(secrets, webhook_id)
        else:
            log.info("no trigger changes")
    else:
        return await set_webhooks(secrets)



# TODO: add paging for > 100 items
# TODO: webhook for new registations -> number memberships
# TODO: mark regs as paid
# TODO: fill out tickets
