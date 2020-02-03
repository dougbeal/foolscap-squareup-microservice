from unittest import mock
from unittest.mock import patch
from unittest.mock import Mock
from unittest.mock import MagicMock
import unittest
import tracemalloc

import main

import google.cloud.logging


@patch('google.cloud.pubsub_v1.PublisherClient', spec=True)
@patch('square.client.Client', spec=True)
@patch('google.cloud.secretmanager.SecretManagerServiceClient', spec=True)
@patch('yaml.load', spec=True)
@patch('asyncio.run', spec=True)
class TestGoogleCloundFunctions(unittest.TestCase):

    def setUp(self):
        main.logging_client = MagicMock(name='logging_client')
        self.request = MagicMock(name='request')
        self.event = MagicMock(name='event')
        self.context = MagicMock(name='context')
        tracemalloc.start()

    def tearDown(self):
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        top_stats = snapshot.statistics('lineno')


    def test_foolscap_square_webhook(self, *mocks):
        main.foolscap_square_webhook(self.request())


    def test_foolscap_tito_webhook(self, *mocks):
        main.foolscap_tito_webhook(self.request)


    def test_foolscap_pubsub_topic_square_change(self, *mocks):
        main.foolscap_pubsub_topic_square_change(self.event, self.context)

    def test_foolscap_pubsub_topic_bootstrap(self, *mocks):
        main.foolscap_pubsub_topic_bootstrap(self.event, self.context)

    def test_foolscap_firestore_registration_document_changed(self, *mocks):
        main.foolscap_firestore_registration_document_changed(self.event, self.context)
