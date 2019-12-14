import asyncio
import concurrent.futures
from pprint import pprint
import logging
import requests
import requests_cache

from jsonpath_rw import jsonpath, parse

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
    membership_item_ids = set()
    locations = []
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
        #pprint(result.body)
        item = result.body["objects"][0]
        membership_item_ids.add(item["id"])
        for variations in item['item_data']['variations']:
            membership_item_ids.add(variations['id'])
            membership_item_ids.add(variations['item_variation_data']['item_id'])
        locations = item['present_at_location_ids']
    elif result.is_error():
        print(result.errors)

    return membership_item_ids, locations

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
        membership_item_ids, locations = await get_membership_items()
        pprint( membership_item_ids )
        memberships = await get_item_orders( membership_item_ids, locations )
        pprint( memberships )

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())


# TODO: switch over to jsonpath to make json access less fragil?
# TODO: write out json files as debugging/cache ? https://realpython.com/caching-external-api-requests/ [sqllite]
#   https://joblib.readthedocs.io/en/latest/generated/joblib.Memory.html (conlusion - doesn't work with async)
#   just set cache timeout and don't worry about it?
#   webhook trigger invalidates cache?
