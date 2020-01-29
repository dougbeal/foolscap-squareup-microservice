import urllib
import os
import logging

import mock
from google.cloud import firestore
import google.auth.credentials

class Storage:
    col0 = collection_name = 'foolscap-microservices'
    col1 = subcollection_name = 'events'
    col2 = subsubcollection_name = 'registrations'

    @classmethod
    def read(cls, name):
        pass

    @classmethod
    def write(cls, name, data):
        pass

class FirestoreStorage(Storage):
    if os.getenv('GAE_ENV', '').startswith('standard'):
        # production
        client = firestore.Client()
    else:
        import logging
        log = logging.getLogger(__name__)
        log.info("storage in localhost mode.")
        # localhost
        os.environ["FIRESTORE_DATASET"] = "test"
        os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8582"
        os.environ["FIRESTORE_EMULATOR_HOST_PATH"] = "localhost:8582/firestore"
        os.environ["FIRESTORE_HOST"] = "http://localhost:8582"
        os.environ["FIRESTORE_PROJECT_ID"] = "test"
        import glob
        cred = glob.glob('secrets/*.json', recursive=False)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred[0]
        credentials = mock.Mock(spec=google.auth.credentials.Credentials)
        client = firestore.Client(project="test", credentials=credentials)

    # ex get_document_reference('tito', '2020')
    # ex get_document_reference('tito', '2021')

    # collection(Storage.collection_name) document('tito') collection('events') document('2020')

    @classmethod
    async def base_collection(cls):
        ref = cls.client.collection(Storage.collection_name)
        return ref

    # foolscap-microservices/tito/events/foolscap-2020/registrations/N4FD
    @classmethod
    async def get_registration_document_reference(cls, service, event, slug):
        log = logging.getLogger(__name__)

        ref = ((await cls.get_event_collection_reference(service, event))
               .document(slug))
        log.debug("document path %s", ref.path)
        return ref


    @classmethod
    async def get_event_collection_reference(cls, service, event):
        log = logging.getLogger(__name__)

        ref = ((await cls.base_collection())
               .document(service).collection(Storage.subcollection_name)
               .document(event).collection(Storage.subsubcollection_name))
        log.debug("collection parent %s", ref.parent.path)
        return ref

    @classmethod
    async def read(cls, name, year='2020'):
        doc_ref = cls.client.collection(Storage.collection_name).document(urllib.parse.quote(name, safe=''))
        return doc_ref.get()

    @classmethod
    async def write(cls, name, data, year='2020'):
        doc_ref = cls.client.collection(Storage.collection_name).document(urllib.parse.quote(name, safe=''))
        return doc_ref.set(data)





def get_storage():
    return FirestoreStorage
