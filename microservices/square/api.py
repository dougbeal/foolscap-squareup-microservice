import asyncio
import concurrent.futures
from pprint import pprint, pformat
import logging
import json
from datetime import datetime, timedelta




from jsonpath_ng import jsonpath, Slice, Fields
from jsonpath_ng.ext import parse
import requests

from .. import storage
from .. import event_year

import microservices

logger = microservices.logger

# FOOLSCAP = "2020"
# FOOLSCAP_MEMBERSHIP = "F20 Membership"
# FOOLSCAP_CATEGORY = f"Foolscap {FOOLSCAP}"
# START_DATE = datetime(int(FOOLSCAP)-1, 1, 1) # tickets are sold at prev foolscap
# END_DATE = datetime(int(FOOLSCAP), 3, 1)


async def get_last_update_date():
    log = logging.getLogger(__name__)
    lastdate = await get_value(['internals', 'updated'])
    if not lastdate:
        lastdate = event_year.earliest_order_date()
    log.debug("last updated %s", lastdate)
    return lastdate

async def get_future_date():
    return datetime(day=1, month=1, year=event_year.years()[-1])+timedelta(days=1)

async def set_update_date(now):
    log = logging.getLogger(__name__)
    log.debug("set updated %s", now)
    await set_value(['internals', 'updated'], now)

async def set_value(path, value):
    await storage.get_storage().set_service_value('square', path, value)

async def get_value(path):
    return await storage.get_storage().get_service_value('square', path)

async def get_foolscap_category(secrets, client):
    log = logging.getLogger(__name__)
    result = client.catalog.search_catalog_objects(
        body = {
            "include_related_objects": True,
            "object_types": [
                             "CATEGORY"
            ],
            "query": {
                "exact_query": {
                    "attribute_name": "name",
                    "attribute_value": FOOLSCAP_CATEGORY
                }
            },
            "limit": 100
        }
    )
    if result.is_success():
        return result.body
    else:
        log.error(result.errors)
        raise result.errors


async def get_foolscap_categories(secrets, client):
    log = logging.getLogger(__name__)
    result = client.catalog.search_catalog_objects(
        body = {
            "include_related_objects": True,
            "object_types": [
                             "CATEGORY"
            ],
            # "query": {
            #     "prefix_query": {
            #         "attribute_name": "category_data.name",
            #         "attribute_prefix": "Fooscap"
            #     }
            # },
            "limit": 100
        }
    )
    if result.is_success():
        log.info("result %s", result)
        return result.body
    else:
        log.error(result.errors)
        raise Exception(result.errors)


#####
# gather all variations of membership (ConCom, AtCon, ...)
# assume they are named starting with a F:
# "F20 ......"
async def get_membership_items(secrets, client):
    membership_item_names = {}
    locations = set()
    result = client.catalog.search_catalog_objects(
        body = {
            "include_related_objects": True,
            "object_types": [
                             "ITEM"
            ],
            "query": {
                "prefix_query": {
                    "attribute_name": "name",
                    "attribute_prefix": "f"
                    }
            },
            "limit": 100
        }
    )

    if result.is_success():
        json_result = result.body

        dats = parse("objects[*]").find(json_result)
        for dat in dats:
            item_id = [f.value for f in Fields('id').find(dat.value)][0]
            item_name = [f.value for f in parse('item_data.name').find(dat.value)][0]

            item_loc = [f.value for f in Fields('present_at_location_ids').find(dat.value)]

            if item_loc:
                item_loc = item_loc[0]

            membership_item_names[item_id] = item_name
            locations.update(item_loc)

            vdats = parse('item_data.variations[*]').find(dat.value)

            for vdat in vdats:
                item_id = [f.value for f in Fields('id').find(vdat.value)][0]
                var_item_name = [f.value for f in parse('item_variation_data.name').find(vdat.value)][0]

                item_loc = [f.value for f in Fields('present_at_location_ids').find(vdat.value)]
                if item_loc:
                    item_loc = item_loc[0]

                composit_name = f"{item_name} - {var_item_name}"
                membership_item_names[item_id] = composit_name
                locations.update(item_loc)

    elif result.is_error():
        print(result.errors)

    logger.log_struct(
        { "membership_item_names": membership_item_names,
         "item locations": list(locations)},
        severity='DEBUG' )
    return membership_item_names, locations


# TODO: store last search date
# /foolscap-microservices/square/
async def get_membership_orders(secrets, client, membership_item_ids, locations):
    log = logging.getLogger(__name__)
    start = await get_last_update_date()
    end = await get_future_date()

    now = datetime.now()
    body = {
        "return_entries": False,
        "limit": 500,
        "location_ids": locations,
        "query": {
            "filter": {
                "date_time_filter": {
                    "closed_at": {
                        "start_at": start.isoformat(),
                        "end_at": end.isoformat()
                    }
                },
                "state_filter": {
                    "states": [
                        "COMPLETED"
                    ]
                }
            },
            "sort": {
                "sort_field": "CLOSED_AT",
                "sort_order": "DESC"
            }
        }
    }
    log.debug("query %s", body)
    result = client.orders.search_orders(body=body)

    log.info("searching for orders in locations %s [%s, %s] body len %i",
              locations, start, end, len(result.body))

    membership_orders = {}
    if result.is_success():
        log.debug("orders: %s", result.body)
        if 'orders' in result.body:
            for order in result.body['orders']:
                order_id = order['id']
                membership = {}
                if 'line_items' in order:
                    membership_items = []
                    membership['order_id'] = order_id
                    membership['line_items'] = membership_items
                    membership['closed_at'] = order['closed_at']
                    for line_item in order['line_items']:
                        if 'catalog_object_id' in line_item:
                            catalog_object_id = line_item['catalog_object_id']
                            if catalog_object_id in membership_item_ids :

                                membership_items.append(line_item)

                                if 'tenders' in order:
                                    tender = order['tenders'][0]
                                    if 'customer_id' in tender:
                                        membership['customer_id'] = tender['customer_id']
                                    else:
                                        membership['customer_id'] = ""

                                #membership['quantity'] = line_item['quantity']
                                #membership['item_id'] = catalog_object_id
                                #membership['item_name'] = membership_item_ids[catalog_object_id]
                    if membership_items:
                        membership_orders[order_id] = membership



    log.debug(membership_orders)
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        orders = membership_orders.values()
        futures = pool.map( get_customer_details, (secrets for membership in orders), (client for membership in orders), ( membership.get('customer_id', None) for membership in orders ) )
        for membership, customer_details in list(zip(orders, await asyncio.gather(*futures))):
            membership['customer'] = customer_details

    await set_update_date(now)
    return membership_orders


async def get_customer_details(secrets, client, customer_id):
    if customer_id:
        result = client.customers.retrieve_customer(
            customer_id = customer_id
            )
        if result.is_success():
            return result.body['customer']
        elif result.is_error():
            print(result.errors)
            return None
    return None

async def write_square_registration(batch, order_id, j):
    log_struct = {}
    event = event_year.active()[0]

    # TODO: current assumption, all items are same foolscap
    query = parse("$..line_items..name")
    match = query.find(j)

    item_names = [m.value for m in match]
    for name in item_names:
        c = event_year.square_item_year_prefix_to_event(name)
        if c:
            event = c
            break

    log_struct['event'] = event
    log_struct['customer_id'] = j.get('customer_id')
    log_struct['item_names'] = item_names
    log_struct['registration'] = j

    if 'event' in j:
        event = j['event']['slug']
    key = order_id
    service = 'square'
    col = await storage.get_storage().get_event_collection_reference(service, event)
    document_reference = col.document(key)
    if not document_reference.get().exists:
        log_struct['message'] = "creating new document for registration"
        batch.create(document_reference, j)
    else:
        log_struct['message'] = "document already exists for registration"
    return log_struct

async def get_registrations(secrets, client):
    membership_item_ids, locations = await get_membership_items(secrets, client)
    memberships = await get_membership_orders( secrets, client, membership_item_ids, locations )

    tasks = []

    batch = await storage.get_storage().start_batch()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for order_id, reg in memberships.items():
            tasks.append(asyncio.create_task(write_square_registration(batch, order_id, reg)))
    log_structs = await asyncio.gather(*tasks)
    batch.commit()
    logger.log_struct(log_structs)
    return memberships

async def get_locations(secrets, client):
    log = logging.getLogger(__name__)
    result = client.locations.list_locations()

    if result.is_success():
        log.debug(result)
        return result.body
    else:
        log.error(result.errors)

async def set_webhook(secrets, client):
    log = logging.getLogger(__name__)
    log.debug("set_webhook")
    json = await get_locations(secrets, client)
    #f = Filter(Expression('status', '!=', "INACTIVE"))
    #log.debug(repr(f))
    #query = Fields('locations').child(Slice())
    query = parse("$..locations[?(@.status='ACTIVE')]", debug=True)
    match = query.find(json)
    log.debug("match %s", match[0].value)

    location_ids = [m.value['id'] for m in match]
    log.debug("location ids " + location_ids)

    # ASSUMPTION: only one active location id

    url = f"https://connect.squareup.com/v1/{location_ids[0]}/webhooks"
    headers = {
        "Authorization": f"Bearer {secrets['metadata']['data']['square']['production']['SQUARE_WEBHOOK_TOKEN']}",
        "Content-Type": "application/json"
    }
    r = requests.put(url,
                     headers = headers,
                     data = '["PAYMENT_UPDATED", "INVENTORY_UPDATED"]'
                     )
    if r.status_code == 404 or r.status_code == 422:
        log.error(f"{r.status_code}: {r.request.url}, {r.request.headers}, {r.request.body}, {r} {r.text}")
    r.raise_for_status()

    json = r.json()
    log.debug(json)
