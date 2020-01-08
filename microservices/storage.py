import urllib
import os

import mock
from google.cloud import firestore
import google.auth.credentials

class Storage:
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
        # localhost
        os.environ["FIRESTORE_DATASET"] = "test"
        os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8582"
        os.environ["FIRESTORE_EMULATOR_HOST_PATH"] = "localhost:8582/firestore"
        os.environ["FIRESTORE_HOST"] = "http://localhost:8582"
        os.environ["FIRESTORE_PROJECT_ID"] = "test"
        credentials = mock.Mock(spec=google.auth.credentials.Credentials)
        client = firestore.Client(project="test", credentials=credentials)    


    @classmethod
    async def read(cls, name):
        doc_ref = cls.client.collection('foolscap-microservies').document(urllib.parse.quote(name, safe=''))
        return doc_ref.get()

    @classmethod
    async def write(cls, name, data):
        doc_ref = cls.client.collection('foolscap-microservies').document(urllib.parse.quote(name, safe=''))
        return doc_ref.set(data)





def get_storage():
    return FirestoreStorage
