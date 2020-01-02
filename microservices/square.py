import asyncio
import concurrent.futures
from pprint import pprint, pformat
import logging
import json
from datetime import datetime
from  os import path

import requests
import requests_cache


from jsonpath_ng.jsonpath import *
from jsonpath_ng import parse

from square.client import Client
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

config = None
with open(path.join(path.dirname(__file__), "..", "secrets.yaml"), "r") as yaml_file:
    config = load(yaml_file, Loader=Loader)

access_token = config['metadata']['data']['square']['production']['SQUARE_ACCESS_TOKEN']

# Create an instance of the API Client
# and initialize it with the credentials
# for the Square account whose assets you want to manage

requests_cache.install_cache('square', backend='sqlite', expire_after=6000)

client = Client(
    access_token=access_token,
    environment='production',
)



FOOLSCAP = "2020"
FOOLSCAP_MEMBERSHIP = "F20 Membership"
FOOLSCAP_CATEGORY = f"Foolscap {FOOLSCAP}"
START_DATE = datetime(int(FOOLSCAP)-1, 1, 1) # tickets are sold at prev foolscap
END_DATE = datetime(int(FOOLSCAP), 3, 1)


async def get_foolscap_category():
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


#####
# gather all variations of membership (ConCom, AtCon, ...)
async def get_membership_items():
    log = logging.getLogger(__name__)
    r = await get_foolscap_category()
    query = Fields('objects').child(Slice()).child(Fields('id'))
    find = query.find(r)
    log.debug(find)

    category_id = find[0].value
    
    log.debug(f"category_id {category_id}")

    if not category_id:
        raise "no category_id"
    membership_item_names = {}
    locations = set()
    result = client.catalog.search_catalog_objects(
        body = {
            "include_related_objects": True,
            "object_types": [
                             "ITEM"
            ],
            "query": {
                "exact_query": {
                    "attribute_name": "category_id",
                    "attribute_value": category_id
                }
            },
            "limit": 100
        }
    )
    if result.is_success():
        json = result.body
        log.debug(pformat(json))

        dats = parse("objects[*]").find(json)
        for dat in dats:
            item_id = [f.value for f in Fields('id').find(dat.value)][0]
            item_name = [f.value for f in parse('item_data.name').find(dat.value)][0]
            
            item_loc = [f.value for f in Fields('present_at_location_ids').find(dat.value)]

            if item_loc:
                item_loc = item_loc[0]

            log.info("%s %s loc:%s", item_id, item_name, item_loc)
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
                log.info("%s %s loc:%s", item_id, composit_name, item_loc)
                membership_item_names[item_id] = composit_name
                locations.update(item_loc)

    elif result.is_error():
        print(result.errors)

    return membership_item_names, locations

async def get_membership_orders(membership_item_ids, locations):
    log = logging.getLogger(__name__)
    log.info("searching for orders in locations %s", pformat(locations))
    result = client.orders.search_orders(
        body = {
            "return_entries": False,
            "limit": 500,
            "location_ids": locations,
            "query": {
                "filter": {
                    "date_time_filter": {
                        "closed_at": {
                            "start_at": START_DATE.isoformat(),
                            "end_at": END_DATE.isoformat()
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
    )

    membership_orders = {}

    if result.is_success():
        log.debug("orders: " + pformat(result.body))
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
                            membership['note'] = membership.get('note', "") + line_item.get('note', "")
                            #membership['quantity'] = line_item['quantity']
                            #membership['item_id'] = catalog_object_id
                            #membership['item_name'] = membership_item_ids[catalog_object_id]
                if membership_items:
                    membership_orders[order_id] = membership



    log.debug(pformat(membership_orders))
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        orders = membership_orders.values()
        futures = pool.map( get_customer_details, ( membership.get('customer_id', None) for membership in orders ) )
        for membership, customer_details in list(zip(orders, await asyncio.gather(*futures))):
            membership['customer'] = customer_details
    return membership_orders


async def get_customer_details(customer_id):
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

async def get_registrations():
    log = logging.getLogger(__name__)    
    membership_item_ids, locations = await get_membership_items()
    log.debug(pformat( membership_item_ids ))
    memberships = await get_membership_orders( membership_item_ids, locations )
    log.debug(pformat( memberships ))
    with open(__file__ + ".json", 'w') as output:
        json.dump(memberships, output)

        
logging.basicConfig(level=logging.INFO)




# TODO, want to create 1 registation per purchase, to make managing easier, and the note seems to be associated with first item
#   can do it here or in sync    
