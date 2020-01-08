from  os import path
import os

from square.client import Client
import requests_cache    
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

secrets = None

def get_data_path():
    return os.path.dirname(__file__)

with open(path.join(get_data_path(), "..", "secrets.yaml"), "r") as yaml_file:
    secrets = load(yaml_file, Loader=Loader)
    

#SQUARE_WEBHOOK_TOKEN = secrets['metadata']['data']['square']['production']['SQUARE_WEBHOOK_TOKEN']

# Create an instance of the API Client
# and initialize it with the credentials
# for the Square account whose assets you want to manage

requests_cache.install_cache('development-cache', backend='sqlite', expire_after=6000)

SQUARE_CLIENT = Client(
    access_token=secrets['metadata']['data']['square']['production']['SQUARE_ACCESS_TOKEN'],
    environment='production',
)



async def source_json(source):
    with open(source, 'r') as f:
        return json.load(f)
