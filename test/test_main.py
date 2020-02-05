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


@patch('requests.delete', create_requests_mock(requests.delete))
@patch('requests.post', create_requests_mock(requests.delete))
@patch('requests.patch', create_requests_mock(requests.delete))
class RegistrationTestTito(TestTito):
    def setUp(self):
        pass

    def tearDown(self):
        pass

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
