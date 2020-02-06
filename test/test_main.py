from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch
from datetime import datetime
import asyncio
import json
import requests
import tracemalloc
import unittest

import main
import microservices.square.api
import microservices.tito.api

import google.cloud.logging

def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper

from microservices import create_requests_mock

@patch('google.cloud.pubsub_v1.PublisherClient', spec=True)
@patch('square.client.Client', spec=True)
@patch('google.cloud.secretmanager.SecretManagerServiceClient', spec=True)
@patch('yaml.load', spec=True)
@patch('microservices.tito.api.storage', spec=microservices.tito.api.storage, mock=AsyncMock())
@patch('microservices.storage', spec=microservices.storage, mock=AsyncMock())
@patch('microservices.storage.get_storage', mock=AsyncMock())
@patch.multiple('microservices.tito.api.requests',
                post=create_requests_mock('requests.post'),
                delete=create_requests_mock('requests.delete'),
                patch=create_requests_mock('requests.patch'),
                get=create_requests_mock('requests.get'))

class TestGoogleCloundFunctions(unittest.TestCase):

    def setUp(self):
        main.logging_client = MagicMock(spec=main.logging_client, name='logging_client')
        main.logger = MagicMock(spec=main.logger, name='logging_client')
        self.request = MagicMock(name='request')
        self.event = MagicMock(name='event')
        self.context = MagicMock(name='context')
        #tracemalloc.start()

    def tearDown(self):
        # snapshot = tracemalloc.take_snapshot()
        # tracemalloc.stop()
        # top_stats = snapshot.statistics('lineno')
        pass


    def test_foolscap_square_webhook(self, *mocks):
        main.foolscap_square_webhook(self.request())
        main.logger.log_struct.assert_called()


    def test_foolscap_tito_webhook(self, *mocks):
        main.foolscap_tito_webhook(self.request)
        main.logger.log_struct.assert_called()

    def test_foolscap_pubsub_topic_square_change(self, *mocks):
        main.foolscap_pubsub_topic_square_change(self.event, self.context)
        main.logger.log_struct.assert_called()

    def test_foolscap_pubsub_topic_bootstrap(self, *mocks):
        main.foolscap_pubsub_topic_bootstrap(self.event, self.context)
        main.logger.log_struct.assert_called()

    def test_foolscap_firestore_registration_document_changed(self, *mocks):
        main.foolscap_firestore_registration_document_changed(self.event, self.context)
        main.logger.log_struct.assert_called()



class TestSquare(unittest.TestCase):
    def setUp(self):
        main.logging_client = MagicMock(name='logging_client')
        main.logger = MagicMock(name='main.logger')
        microservices.square.api.logger = MagicMock(name='logger')

    def tearDown(self):
        pass

    @patch('logging.getLogger', spec=True)
    @patch('jsonpath_ng.ext.parse', spec=True)
    @patch('microservices.storage', spec=microservices.storage)
    @patch('microservices.square.api.get_membership_orders', mock=MagicMock(microservices.square.api.get_membership_orders, return_value={ 'order_id': MagicMock()}))
    @async_test
    async def test_write_square_registration(self, logging, query, gmo, *mocks):
        query_data = [{'value': 'aname'} ]
        data = {'customer_id': 'cu'}

        query.find = MagicMock(
            name='query.find',
            return_value=data)
        logs = await microservices.square.api.write_square_registration(
            MagicMock(name='batch'),
            'key',
            data)
        self.assertTrue(logs)


class TestTito(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

class TestTitoRealLogging(TestTito):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @async_test
    async def test_get_tito_generic_logging():
        from microservices import development_config as config
        secrets = config.secrets
        foo = await microservices.tito.api.get_tito_generic(
            secrets, 'webhooks', 'foolscap-2020')

class TestTitoMockLogging(TestTito):
    def setUp(self):
        main.logging_client = MagicMock(name='logging_client')
        main.logger = MagicMock(name='main.logger')
        microservices.tito.api.logger = MagicMock(name='logger')
        microservices.square.api.logger = MagicMock(name='logger')

    def tearDown(self):
        pass

    @patch('logging.getLogger', spec=True)
    @patch('jsonpath_ng.ext.parse', spec=True)
    @patch('microservices.storage', spec=True)
    @patch.multiple('microservices.tito.api.requests',
                post=create_requests_mock('requests.post'),
                delete=create_requests_mock('requests.delete'),
                patch=create_requests_mock('requests.patch'),
                get=create_requests_mock('requests.get'))
    @async_test
    async def test_get_tito_generic(self, logging, query, *mocks):
        secrets = MagicMock(name='secret')
        name = 'name'
        event = 'event-2222'
        params = {}

        result = await microservices.tito.api.get_tito_generic(
            secrets,
            name,
            event,
            params )

        microservices.tito.api.logger.log_struct.assert_called()

class SquareNameExtraction(TestTito):
    def setUp(self):
        self.patches = []
        self.patches.append(patch('requests.delete', create_requests_mock(requests.delete)))
        self.patches.append(patch('requests.post', create_requests_mock(requests.delete)))
        self.patches.append(patch('requests.patch', create_requests_mock(requests.delete)))

    def tearDown(self):
        for p in self.patches:
            p.stop()
    

    def test_convert_square_registration(self, *mock):
        note = "Test User\nTest.user,email@dougbeal.com"
        update = microservices.tito.api.convert_square_registration(
            {},
            {},
            note,
            0)
        self.assertEqual(update.get('answers', {}).get('badge-name'), 'Test User')

    def test_convert_square_registration_two_tickets(self, *mock):
        note = "Test User\nTest User2\ntestemail@foo.bar"
        update = microservices.tito.api.convert_square_registration(
            {},
            {},
            note,
            1)
        self.assertEqual(update.get('answers', {}).get('badge-name'), 'Test User2')

    def test_convert_square_registration_email_after_name(self, *mock):
        note = "Test User testemail@foo.bar"
        update = microservices.tito.api.convert_square_registration(
            {},
            {},
            note,
            0)
        self.assertEqual(update.get('answers', {}).get('badge-name'), 'Test User')

    def test_convert_square_registration_long_name(self, *mock):
        note = "Title Test Middle Last Last Last testemail@foo.bar"
        update = microservices.tito.api.convert_square_registration(
            {},
            {},
            note,
            0)
        self.assertEqual(update.get('answers', {}).get('badge-name'), 'Title Test Middle Last Last Last')                        


# TODO: requests patch not right        
class RegistrationTestTito(TestTito):
    def setUp(self):
        self.patches = []

        self.patches.append(
            patch.multiple('microservices.tito.api.requests',
                post=create_requests_mock(requests.post),
                delete=create_requests_mock(requests.delete),
                patch=create_requests_mock(requests.patch),
                get=create_requests_mock(requests.get))
            )

        self.patches.append(
            patch.multiple('requests',
                post=create_requests_mock(requests.post),
                delete=create_requests_mock(requests.delete),
                patch=create_requests_mock(requests.patch),
                get=create_requests_mock(requests.get))
            )        
        self.patches.append(patch('requests.delete', create_requests_mock(requests.delete)))
        self.patches.append(patch('requests.post', create_requests_mock(requests.delete)))
        self.patches.append(patch('requests.patch', create_requests_mock(requests.delete)))

    def tearDown(self):
        for p in self.patches:
            p.stop()
    

    @patch('microservices.tito.api.read_registrations',
           spec=microservices.tito.api.read_registrations,
           return_value={
               "foolscap-microservices": {
                   "tito": {
                       "events": {
                           "foolscap-2020": {
                               "registrations": [{
                                   'name': 'notfromsquare',
                                   'completed_at': datetime(1000,10,2).isoformat(),
                                   'tickets': [
                                               ]
                                   },{
                                       'name': 'fromsquare',
                                       'source': 'fromsquare',
                                       'tickets': [
                                               ]
                                       }


                                                 ]
                               },
                           "foolscap-2021": {
                               "registrations": []
                               },
                               }
                               },
                   "square": {
                       "events": {
                           "foolscap-2020": {
                               "registrations": [{
                                   'name': 'fromsquare',
                                   'order_id': 'fromsquare',
                                   'closed_at': datetime(1000,10,1).isoformat(),
                                   'line_items': [

                                                  ]
                                   }
                                                 ]
                               },
                           "foolscap-2021": {
                               "registrations": []
                               },
                        }
                        },
                        }
                        }
           )

    @async_test
    async def test_sync_event(self, *mock):
        from microservices import development_config as config
        secrets = config.secrets
        foo = await microservices.tito.api.sync_active(secrets)

    @patch('microservices.tito.api.read_registrations',
           spec=microservices.tito.api.read_registrations,
           return_value={
               "foolscap-microservices": {
                   "tito": {
                       "events": {
                           "foolscap-2020": {
                               "registrations": []
                               },
                           "foolscap-2021": {
                               "registrations": []
                               },
                               }
                               },
                   "square": {
                       "events": {
                           "foolscap-2020": {
                               "registrations": []
                               },
                "foolscap-2021": {
                    "registrations": [
                        {
                            "closed_at": "2020-02-05T22:27:39Z",
                            "order_id": "8QaWHuQfdabbQIKFU8uxydyeV",
                            "line_items": [
                                {
                                    "gross_sales_money": {
                                        "amount": 5000,
                                        "currency": "USD"
                                    },
                                    "name": "F21 Membership",
                                    "note": "Test User\nTest.user,email@dougbeal.com",
                                    "total_money": {
                                        "currency": "USD",
                                        "amount": 5000
                                    },
                                    "base_price_money": {
                                        "amount": 5000,
                                        "currency": "USD"
                                    },
                                    "catalog_object_id": "LEJDSLBKOJ2T6ZJ5FL5JDCPP",
                                    "uid": "59ED7648-4113-48E2-8ECB-A78271E65AE3",
                                    "quantity": "1",
                                    "variation_total_price_money": {
                                        "amount": 5000,
                                        "currency": "USD"
                                    },
                                    "total_discount_money": {
                                        "amount": 0,
                                        "currency": "USD"
                                    },
                                    "variation_name": "Early Bird",
                                    "total_tax_money": {
                                        "amount": 0,
                                        "currency": "USD"
                                    }
                                }
                            ],
                            "customer": None,
                            "customer_id": ""
                        },
                        {
                            "closed_at": "2020-02-01T03:13:14Z",
                            "order_id": "k8nit33rNXBUEr4bkE1rIyMF",
                            "line_items": [
                                {
                                    "uid": "B3379EAB-E6E6-4FC0-804D-E3C585A515A7",
                                    "quantity": "1",
                                    "gross_sales_money": {
                                        "amount": 5000,
                                        "currency": "USD"
                                    },
                                    "name": "F21 Membership",
                                    "variation_total_price_money": {
                                        "amount": 5000,
                                        "currency": "USD"
                                    },
                                    "total_money": {
                                        "currency": "USD",
                                        "amount": 5000
                                    },
                                    "total_discount_money": {
                                        "currency": "USD",
                                        "amount": 0
                                    },
                                    "variation_name": "Early Bird",
                                    "total_tax_money": {
                                        "currency": "USD",
                                        "amount": 0
                                    },
                                    "base_price_money": {
                                        "currency": "USD",
                                        "amount": 5000
                                    },
                                    "catalog_object_id": "LEJDSLBKOJ2T6ZJ5FL5JDCPP"
                                }
                            ],
                            "customer": {
                                "created_at": "2020-02-02T00:41:55.635Z",
                                "groups": [
                                    {
                                        "name": "Reachable",
                                        "id": "BQH2PF2ZQK4SP.REACHABLE"
                                    }
                                ],
                                "creation_source": "DIRECTORY",
                                "family_name": "Uer",
                                "email_address": "test@dougbeal.com",
                                "id": "6XCQR574G954HADQC6J2ZE2RSW",
                                "given_name": "Test",
                                "updated_at": "2020-02-02T09:16:48Z",
                                "preferences": {
                                    "email_unsubscribed": False
                                }
                            },
                            "customer_id": "6XCQR574G954HADQC6J2ZE2RSW"
                        }
                    ]
                }
            }
                       }}})

    @async_test
    async def test_sync_events_from_square(self, *mock):
        from microservices import development_config as config
        secrets = config.secrets
        foo = await microservices.tito.api.sync_active(secrets)


        
