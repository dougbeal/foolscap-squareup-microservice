from  os import path

from square.client import Client
import requests_cache    
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

secrets = None    
with open(path.join(path.dirname(__file__), "..", "secrets.yaml"), "r") as yaml_file:
    secrets = load(yaml_file, Loader=Loader)
    

#SQUARE_WEBHOOK_TOKEN = secrets['metadata']['data']['square']['production']['SQUARE_WEBHOOK_TOKEN']

# Create an instance of the API Client
# and initialize it with the credentials
# for the Square account whose assets you want to manage

requests_cache.install_cache('square', backend='sqlite', expire_after=6000)

SQUARE_CLIENT = Client(
    access_token=secrets['metadata']['data']['square']['production']['SQUARE_ACCESS_TOKEN'],
    environment='production',
)
