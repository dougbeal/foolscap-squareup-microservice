from datetime import datetime
from unittest import mock
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
import asyncio
import inspect
import json
import requests
import tracemalloc
import unittest
import sys




import main
import microservices.square.api
import microservices.tito.api
import microservices.development_config
from microservices import create_requests_mock, create_requests_mock_settings

import google.cloud.logging
from flask import Request as google_http_trigger_request
from jsonpath_ng import jsonpath, Slice, Fields, Root
from jsonpath_ng.ext import parse




class TestTito(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.secrets = MagicMock(name='secrets', autospec=microservices.development_config.secrets)
        self.patches = []
        self.requests = {}
        self.patchRequestSetUp()

    def tearDown(self):
        super().tearDown()
        self.patchRequestTearDown()
        for p in self.patches:
            p.stop()

    def patchRequestSetUp(self):
        mod = 'microservices.tito.api.requests'

        for fn in [
                   requests.post,
                   requests.delete,
                   requests.patch,
                   requests.put,
                   requests.get
                   ]:

            if not isinstance(fn, Mock):
                name = fn.__name__
                p = patch(
                    '.'.join([mod, name]), new=create_requests_mock(fn))
                self.patches.append(p)
                self.requests[name] = p.start()
            else:
                fn.mock_reset()

    def patchRequestTearDown(self):
        pass

    def assertOtherRequestNotCalled(self, name):
        for k, v in self.requests.items():
            if name == k:
                continue
            v.assert_not_called()

    def assertRequestCalled(self, name, *args, **kwargs):
        self.requests[name].assert_called_once()

    def assertRequestCalledOnceWith(self, name, *args, **kwargs):
        self.requests[name].assert_called_once_with(*args, **kwargs)


class TestGoogleCloundFunctions(TestTito):
    def setUp(self):
        super().setUp()
        main.logging_client = MagicMock(spec=main.logging_client, name='logging_client')
        main.logger = MagicMock(spec=main.logger, name='logging_client')
        self.request = MagicMock(
            name='request',
            autospec=google_http_trigger_request,
            text='{ "some_json": "foo" }',
            **{ 'get_json.return_value':{
                'reference': '___KJ45_TITO_REG_KEY',
                'event': {
                    'slug': 'foolscap-2020',
                    'completed_at': datetime(1000,11,2).isoformat()
                    },
                 }})
        self.event = MagicMock(name='event')
        self.context = MagicMock(name='context')
        self.patches.append(
            patch('google.cloud.pubsub_v1.PublisherClient', autospec=True))
        self.patches.append(
            patch('google.cloud.firestore_v1.client.Client', autospec=True))
        self.patches.append(
            patch('square.client.Client', autospec=True))
        self.patches.append(
            patch('google.cloud.secretmanager.SecretManagerServiceClient', autospec=True))
        self.patches.append(
            patch('yaml.load', autospec=True))
        self.patches.append(
            patch.object(microservices.storage.FirestoreStorage,
                         'client',
                         autospec=True))
        # self.patches.append(
        #     patch('microservices.tito.api.storage.get_storage',
        #     autospec=True,
        #     return_value=AsyncMock(name='storage')))

        self.patches.append(patch('microservices.tito.api.read_registrations',
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
           ))
        #tracemalloc.start()
        main.secrets = self.secrets
        for p in self.patches:
            p.start()

    def tearDown(self):
        super().tearDown()
        # snapshot = tracemalloc.take_snapshot()
        # tracemalloc.stop()
        # top_stats = snapshot.statistics('lineno')



    def test_secrets_mock(self):
        self.assertIsInstance(self.secrets, Mock)

    def test_firestore_client_mock(self):
        self.assertIsInstance(google.cloud.firestore_v1.client.Client, Mock)

    def test_foolscap_square_webhook(self, *mocks):
        main.foolscap_square_webhook(self.request)
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
        context = MagicMock(name='context',
                            resource='/documents/foolscap-microservices/square/events/foolscap-2020/registrations/iFW3b8l2DZWQBmzqAtiMGvMF')
        # self.assertIs(
        #     type(microservices.tito.api.storage.FirestoreStorage.client),
        #     unittest.mock.NonCallableMock)
        main.foolscap_firestore_registration_document_changed(self.event, context)
        main.logger.log_struct.assert_called()



class TestSquare(unittest.TestCase):
    def setUp(self):
        main.logging_client = MagicMock(name='logging_client')
        main.logger = MagicMock(name='main.logger')
        microservices.square.api.logger = MagicMock(name='logger')

    def tearDown(self):
        pass

    def test_write_square_registration(self):
        fn = self.do_test_write_square_registration
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(fn())

    @patch('logging.getLogger', autospec=True)
    @patch('jsonpath_ng.ext.parse', autospec=True)
    @patch('microservices.storage', autospec=microservices.storage)
    @patch('microservices.square.api.get_membership_orders', mock=MagicMock(microservices.square.api.get_membership_orders, return_value={ 'order_id': MagicMock()}))
    async def do_test_write_square_registration(self, logging, query, gmo, *mocks):
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



class TestTitoMock(TestTito):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_secrets_mock(self):
        self.assertIsInstance(self.secrets, Mock)

    def test_requests_paging(self):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(self.do_test_requests_paging())

    async def do_test_requests_paging(self):
        mod = 'microservices.tito.api.requests'

        secrets = self.secrets
        event = 'foolscap-2021'
        name = 'releases'
        fn = 'get'
        name = 'registrations'

        r = await microservices.tito.api.get_tito_generic(self.secrets, name, event)

        self.assertRequestCalled(fn)
        self.assertRequestCalledOnceWith(fn,
            microservices.tito.api.tito_api_url(event, name),
            headers = microservices.tito.api.get_write_headers(self.secrets),
            params = {})
        self.assertOtherRequestNotCalled(fn)
        self.requests[fn].reset_mock()        
        
    def test_requests_fns(self):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(self.do_test_requests_fns())

    async def do_test_requests_fns(self):
        mod = 'microservices.tito.api.requests'

        secrets = self.secrets
        event = 'foolscap-2021'
        name = 'releases'
        fn = 'get'
        self.assertTrue(self.requests)
        r = await microservices.tito.api.get_tito_release_names(self.secrets, event)

        self.assertRequestCalled(fn)
        self.assertRequestCalledOnceWith(fn,
            microservices.tito.api.tito_api_url(event, name),
            headers = microservices.tito.api.get_base_headers(self.secrets),
            params = {})
        self.assertOtherRequestNotCalled(fn)
        self.requests[fn].reset_mock()

        name = 'registrations'
        fn = 'post'
        registration = { 'name': 'ThisIsRegistration', }
        r = await microservices.tito.api.put_tito_generic(self.secrets, event, name,
              registration
              )

        self.assertRequestCalled(fn)
        self.assertRequestCalledOnceWith(fn,
            microservices.tito.api.tito_api_url(event, name),
            headers = microservices.tito.api.get_write_headers(self.secrets),
            json = registration)
        self.assertOtherRequestNotCalled(fn)
        self.requests[fn].reset_mock()

        r = await microservices.tito.api.put_tito_generic(self.secrets, event, name,
              json = registration,
              operation = microservices.tito.api.requests.post
              )

        self.assertRequestCalled(fn)
        self.assertRequestCalledOnceWith(fn,
            microservices.tito.api.tito_api_url(event, name),
            headers = microservices.tito.api.get_write_headers(self.secrets),
            json = registration)
        self.assertOtherRequestNotCalled(fn)
        self.requests[fn].reset_mock()

        fn = 'patch'

        r = await microservices.tito.api.put_tito_generic(self.secrets, event, name,
              json = registration,
              operation = microservices.tito.api.requests.patch
              )

        self.assertRequestCalled(fn)
        self.assertRequestCalledOnceWith(fn,
            microservices.tito.api.tito_api_url(event, name),
            headers = microservices.tito.api.get_write_headers(self.secrets),
            json = registration)

        self.assertOtherRequestNotCalled(fn)
        self.requests[fn].reset_mock()


class TestTitoRealLogging(TestTito):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_get_tito_generic_logging(self):
        frame = inspect.currentframe()
        fname = inspect.getframeinfo(frame).function
        fn = getattr(self, "do_" + fname)
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(fn())

    async def do_test_get_tito_generic_logging(self):
        from microservices import development_config as config
        foo = await microservices.tito.api.get_tito_generic(
            self.secrets, 'webhooks', 'foolscap-2020')

class TestTitoMockLogging(TestTito):
    def setUp(self):
        super().setUp()
        main.logging_client = MagicMock(name='logging_client')
        main.logger = MagicMock(name='main.logger')
        microservices.tito.api.logger = MagicMock(name='logger')
        microservices.square.api.logger = MagicMock(name='logger')

    def tearDown(self):
        super().tearDown()

    def test_get_tito_generic(self):
        frame = inspect.currentframe()
        fname = inspect.getframeinfo(frame).function
        fn = getattr(self, "do_" + fname)
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(fn())

    @patch('logging.getLogger', spec=True)
    @patch('jsonpath_ng.ext.parse', spec=True)
    @patch('microservices.storage', spec=True)
    async def do_test_get_tito_generic(self, logging, query, *mocks):
        name = 'name'
        event = 'event-2222'
        params = {}

        result = await microservices.tito.api.get_tito_generic(
            self.secrets,
            name,
            event,
            params )

        microservices.tito.api.logger.log_struct.assert_called()

class SquareNameExtraction(TestTito):
    def setUp(self):
        super().setUp()

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
        super().setUp()

    def tearDown(self):
        super().tearDown()
        for p in self.patches:
            p.stop()
        self.patchRequestTearDown()

    def test_sync_event(self):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(self.do_test_sync_event())

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
    async def do_test_sync_event(self, read_registrations, *mock):
        from microservices import development_config as config
        foo = await microservices.tito.api.sync_active(self.secrets)



    def test_sync_events_from_square(self):
        frame = inspect.currentframe()
        fname = inspect.getframeinfo(frame).function
        fn = getattr(self, 'do_' + fname)
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(fn())

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

    async def do_test_sync_events_from_square(self, *mock):
        from microservices import development_config as config
        foo = await microservices.tito.api.sync_active(self.secrets)

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
                                },
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
    @patch('microservices.tito.api.get_tito_release_names',
           return_value=(['Early Bird'], {'Early Bird': 'EB Release id'}))
    @patch('microservices.tito.api.square_ticket_tito_name',
           return_value='Early Bird')
    async def do_test_sync_events_from_square_two_tickets(self, *mock):
        #from microservices import development_config as config
        r = await microservices.tito.api.sync_active(self.secrets)
        return r

    def test_sync_events_from_square_two_tickets(self, *mock):
        import tracemalloc
        tracemalloc.start()
        loop = asyncio.new_event_loop()
        val = loop.run_until_complete(self.do_test_sync_events_from_square_two_tickets())

        self.assertEqual(len(val), 2)
        self.assertEqual(type(val), type([]))
        for v in val:
            self.assertTrue(v[0].startswith('foolscap-'))
            self.assertEqual(type(v[1]), type([]))

        self.assertEqual(len(val[1][1]), 2)
        order_ids = ["8QaWHuQfdabbQIKFU8uxydyeV", "k8nit33rNXBUEr4bkE1rIyMF"]
        for source in [v['source'] for v in val[1][1]]:
            self.assertIn( source, order_ids)
