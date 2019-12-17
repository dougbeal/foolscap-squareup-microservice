import asyncio
import concurrent.futures
from pprint import pprint, pformat
import logging
import json

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
with open("secrets.yaml", "r") as yaml_file:
    config = load(yaml_file, Loader=Loader)

access_token = config['SQUARE_ACCESS_TOKEN']
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

#####
# gather all variations of membership (ConCom, AtCon, ...)
async def get_membership_items():
    log = logging.getLogger(__name__)
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
                    "attribute_prefix": FOOLSCAP_MEMBERSHIP
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
            item_loc = [f.value for f in Fields('present_at_location_ids').find(dat.value)][0]
            item_name = [f.value for f in parse('item_data.name').find(dat.value)][0]
            log.debug("%s %s %s", item_id, item_loc, item_name)
            membership_item_names[item_id] = item_name
            locations.update(item_loc)

            vdats = parse('item_data.variations[*]').find(dat.value)
            
            for vdat in vdats:
                item_id = [f.value for f in Fields('id').find(vdat.value)][0]
                item_loc = [f.value for f in Fields('present_at_location_ids').find(vdat.value)][0]                
                item_name = [f.value for f in parse('item_variation_data.name').find(vdat.value)][0]
                log.debug("%s %s %s", item_id, item_loc, item_name)                
                membership_item_names[item_id] = item_name
                locations.update(item_loc)                

    elif result.is_error():
        print(result.errors)

    return membership_item_names, locations

async def get_item_orders(membership_item_ids, locations):
    result = client.orders.search_orders(
        body = {
            "return_entries": False,
            "limit": 500,
            "location_ids": locations,
            "query": {
                "filter": {
                    "date_time_filter": {
                        "closed_at": {
                            "start_at": "2018-03-03T20:00:00+00:00",
                            "end_at": "2019-03-04T21:54:45+00:00"
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

    membership_orders = []
    membership_items = []
    memberships = []
    if result.is_success():
        #pprint(result.body)
        for order in result.body['orders']:
            #pprint(order)
            if 'line_items' in order:
                #pprint(order)
                for line_item in order['line_items']:
                    if 'catalog_object_id' in line_item:
                        catalog_object_id = line_item['catalog_object_id']
                        if catalog_object_id in membership_item_ids :
                            membership_orders.append(order)
                            membership_items.append(line_item)
                            membership = {}
                            membership['order_id'] = order['id']
                            if 'tenders' in order:
                                tender = order['tenders'][0]
                                if 'customer_id' in tender:
                                    membership['customer_id'] = tender['customer_id']
                                else:
                                    membership['customer_id'] = ""
                            membership['note'] = line_item.get('note', "")
                            membership['quantity'] = line_item['quantity']
                            membership['item_id'] = catalog_object_id
                            membership['item_name'] = membership_item_ids[catalog_object_id]
                            memberships.append(membership)




    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = pool.map( get_customer_details, ( membership.get('customer_id', None) for membership in memberships ) )
        for membership, customer_details in list(zip(memberships, await asyncio.gather(*futures))):
            membership['customer'] = customer_details
    return memberships


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

async def main():
    membership_item_ids, locations = await get_membership_items()
    pprint( membership_item_ids )
    memberships = await get_item_orders( membership_item_ids, locations )
    pprint( memberships )
    with open(__file__ + ".json", 'w') as output:
        json.dump(memberships, output)

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main())
except:
    import pdb, traceback
    traceback.print_exc()
    pdb.post_mortem()


# TODO: export data
# TODO: switch over to jsonpath to make json access less fragil?
