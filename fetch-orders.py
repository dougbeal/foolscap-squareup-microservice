from pprint import pprint

from jsonpath_rw import jsonpath, parse

from square.client import Client
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

config = load(open("secrets.yaml", "r"), Loader=Loader)

access_token = config['SQUARE_ACCESS_TOKEN']
# Create an instance of the API Client
# and initialize it with the credentials
# for the Square account whose assets you want to manage

client = Client(
    access_token=access_token,
    environment='production',
)

# # Get an instance of the Square API you want call
# api_locations = client.locations

# # Call list_locations method to get all locations in this Square account
# locations = result = api_locations.list_locations()
# # Call the success method to see if the call succeeded
# if result.is_success():
#     # The body property is a list of locations
#     locations = result.body['locations']
#     # Iterate over the list
#     for location in locations:
#         # Each location is represented as a dictionary
#         for key, value in location.items():
#             print(f"{key} : {value}")
#         print("\n")
# # Call the error method to see if the call failed
# elif result.is_error():
#     print('Error calling LocationsApi.listlocations')
#     errors = result.errors
#     # An error is returned as a list of errors
#     for error in errors:
#         # Each error is represented as a dictionary
#         for key, value in error.items():
#             print(f"{key} : {value}")
#         print("\n")

# api_catalog = client.catalog

# catagories = result = api_catalog.list_catalog(types="CATEGORY")
# print([i['category_data']['name'] for i in result.body['objects']])

CATEGORY_TARGET="Foolscap 2020"

result = client.catalog.search_catalog_objects(
    body = {
        "object_types": [
                         "CATEGORY"
        ],
        "query": {
            "prefix_query": {
                "attribute_name": "name",
                "attribute_prefix": CATEGORY_TARGET
            }
        },
        "limit": 100
    }
)

category_id = None
if result.is_success():
    #pprint(result.body)
    category_id = result.body["objects"][0]["id"]
elif result.is_error():
    print(result.errors)

# result = client.catalog.search_catalog_objects(
#     body = {
#         "object_types": [
#                          "ITEM"
#         ],
#         "query": {
#             "prefix_query": {
#                 "attribute_name": "category_id",
#                 "attribute_prefix": category_id
#             }
#         },
#         "limit": 100
#     }
# )
# if result.is_success():
#     print(result.body)
# elif result.is_error():
#     print(result.errors)

membership_item_id = set()
locations = None

result = client.catalog.search_catalog_objects(
    body = {
        "include_related_objects": True,
        "object_types": [
                         "ITEM"
        ],
        "query": {
            "prefix_query": {
                "attribute_name": "name",
                "attribute_prefix": "F20 Membership"
            }
        },
        "limit": 100
    }
)
if result.is_success():
    #pprint(result.body)
    item = result.body["objects"][0]
    membership_item_id.add(item["id"])
    for variations in item['item_data']['variations']:
        membership_item_id.add(variations['id'])
        membership_item_id.add(variations['item_variation_data']['item_id'])
    locations = item['present_at_location_ids']
elif result.is_error():
    print(result.errors)

pprint(membership_item_id)

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
                    if catalog_object_id in membership_item_id :
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






for membership in memberships:
    if membership['customer_id']:
        result = client.customers.retrieve_customer(
            customer_id = membership['customer_id']
        )

        if result.is_success():
            membership['customer'] = result.body['customer']
        elif result.is_error():
            print(result.errors)


pprint(memberships)
