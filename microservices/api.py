import asyncio
from pprint import pprint

from dateutil.parser import isoparse
from jsonpath_ng import jsonpath, Slice, Fields, Root
from jsonpath_ng.ext import parse

import microservices.util
import microservices.square.api
import microservices.tito.api
import microservices.tito.main



async def print_members(secrets, client, event):
    print(f"event {event}")
    year = int(event.split('-')[1])

    # hack because tito naming changed
    if year < 2020:
        event = str(year)

    square_registrations = await microservices.square.api.get_membership_orders_for_foolscap(secrets, client, year)
    
    banq = []
    deal = []
    memb = []
    square_by_date = sorted(square_registrations, key=lambda reg: isoparse(reg['closed_at']))
    for num, reg in enumerate(square_by_date):
        query = parse("customer..email_address|given_name|family_name")
        match = query.find(reg)
        customer = ' '.join([m.value for m in match])
        query = parse("$..note")
        match = query.find(reg)
        note = ' '.join([m.value for m in match])
        note = ' '.join(note.split('\n'))
        query = parse("order_id")
        match = query.find(reg)
        ref = ' '.join([m.value for m in match])
        for inum, item in enumerate(reg['line_items']):
            query = parse("quantity|variation_name|name")
            match = query.find(item)
            itemname = ' '.join([m.value for m in match])
            deets = f"{num}:{inum} {reg['closed_at']} {ref} - {customer} - {itemname} - {note}"
            if 'Banq' in itemname or 'Bite' in itemname:
                banq.append(deets)
            elif 'Dealer' in itemname:
                deal.append(deets)
            else:
                memb.append(deets)
    width = 200
    print(f"dealers {len(deal)}")
    pprint(deal, width=width)
    print(f"banquet {len(banq)}")
    pprint(banq, width=width)
    print(f"members {len(memb)} square")
    pprint(memb, width=width)
    print('------------------------------')
    total = len(deal)+len(banq)+len(memb)
    print(f"total {total}")
    print('==============================')
    tbanq = []
    tdeal = []
    tmemb = []
    tito_registrations = await microservices.tito.api.get_tito_generic(secrets, 'registrations', event, params={ 'view': 'extended' })
    tito_by_date = sorted(tito_registrations['registrations'], key=lambda item: isoparse(item['completed_at']))

    for num, reg in enumerate(tito_by_date):
        query = parse("source|reference")
        match = query.find(reg)
        ref = f"{reg.get('source')} {reg.get('reference')}"

        query = parse("tickets..badge_number|badge_number|registration_name|registration_email")
        match = query.find(reg)
        customer = ' '.join([m.value for m in match if m.value])
        for inum, item in enumerate(reg['tickets']):
            query = parse("$..release_title|reference")
            match = query.find(item)
            itemname = ' '.join([m.value for m in match])
            deets = f"{num}:{inum} {reg['created_at']} {ref} - {customer} - {itemname}"
            deets.replace('\n', '')
            if 'Banq' in itemname or 'Bite' in itemname:
                tbanq.append(deets)
            elif 'Dealer' in itemname:
                tdeal.append(deets)
            else:
                tmemb.append(deets)
    print(f"dealers {len(tdeal)}")
    pprint(tdeal, width=width)
    print(f"banquet {len(tbanq)}")
    pprint(tbanq, width=width)
    print(f"members {len(tmemb)}")
    pprint(tmemb, width=width)
    print('------------------------------')
    total = len(tdeal)+len(tbanq)+len(tmemb)
    print(f"total {total}")

async def bootstrap(secrets, client):
    tasks = []
    tasks.append(asyncio.create_task(microservices.square.api.get_registrations(secrets, client)))
    tasks.append(asyncio.create_task(microservices.tito.api.get_registrations(secrets)))
    await asyncio.gather(*tasks)
    tasks.clear()
    tasks.append(asyncio.create_task(microservices.tito.api.sync_active(secrets)))
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    import logging

    def bootstrap_main(level=logging.DEBUG):
        microservices.util.async_entry_point(bootstrap, level, secrets, client)

    def members_main(event, level=logging.DEBUG):
        microservices.util.async_entry_point(print_members, level, secrets, client, event)

    PRODUCTION = False
    import fire
    import sys
    import microservices.development_config as config
    secrets = config.secrets
    client = config.SQUARE_CLIENT
    dry_run = True
    if '--mode-production' in sys.argv:
        sys.argv.remove('--mode-production')
        microservices.tito.api.TITO_MODE = 'production'
        dry_run = False
    elif '--mode-production-dry-run' in sys.argv:
        sys.argv.remove('--mode-production-dry-run')
        microservices.tito.api.TITO_MODE = 'production'
        dry_run = True
    elif '--mode-test' in sys.argv:
        sys.argv.remove('--mode-test')
        microservices.tito.api.TITO_MODE = 'test'
        dry_run = False
    else:
        if '--mode-test-dry-run' in sys.argv:
            sys.argv.remove('--mode-test-dry-run')
        microservices.tito.api.TITO_MODE = 'test'
        dry_run = True
    if dry_run:
        print("running dry, with mocked requests.post, requests.patch, and requests.delete")
        print("TITO_MODE " + microservices.tito.api.TITO_MODE)

        from unittest.mock import patch
        from microservices import create_requests_mock as crm
        import requests
        mod = 'microservices.tito.api.requests'
        @patch(mod + '.delete', crm(requests.delete))
        @patch(mod + '.post', crm(requests.post))
        @patch(mod + '.patch', crm(requests.patch))
        def mocked_function():
            return fire.Fire()
        mocked_function()
    else:
        fire.Fire()
