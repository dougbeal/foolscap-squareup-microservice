from pprint import pformat
import os
import asyncio
import json

from google.cloud import pubsub_v1
from google.cloud import secretmanager
import square.client
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader



secrets = {}
logging_client = None
pubsub_client = None
square_client = None
secret_client = None
secrets = None
secret_name = "secrets"

project_id = "foolscap-microservices"

import microservices
logger = microservices.logger

import microservices.square.api
import microservices.tito.api
import microservices.api
import microservices.event_year

def setup_resources():
    global pubsub_client, square_client, secret_client, secrets
    if not pubsub_client:
        pubsub_client = pubsub_v1.PublisherClient()

    if not secret_client:
        secret_client = secretmanager.SecretManagerServiceClient()
    if not secrets:
        resource_name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = secret_client.access_secret_version(resource_name)
        secrets = yaml.load(response.payload.data.decode('UTF-8'), Loader=Loader)
    if not square_client:
        square_client = square.client.Client(
            access_token=secrets['metadata']['data']['square']['production']['SQUARE_ACCESS_TOKEN'],
            environment='production' )

def foolscap_square_webhook(request):
    setup_resources()

    # TODO project_id = "Your Google Cloud Project ID"
    # TODO topic_name = "Your Pub/Sub topic name"
    topic_path = pubsub_client.topic_path(project_id,
                                      'square.change')

     # data must be a bytestring.
    data = "foolscap_square_webhook".encode("utf-8")
    future = pubsub_client.publish(topic_path, data=data, origin="webhook")
    logger.log_struct( {
        'topic_path': topic_path,
        'request': request.__dict__,
        'request.data': request.get_data(),
        'future.result': future.result() } )

def foolscap_tito_webhook(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
    Returns:
        <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
    """
    setup_resources()

    request_json = request.get_json(silent=True)
    request_args = request.args
    text = request_json['text']
    event = request_json['event']['slug']



    log = asyncio.run(microservices.tito.api.write_tito_registration(request_json))
    logger.log_struct( {
        'request': request.__dict__,
        'requestjson': request_json,
        'registrations': log} )

def foolscap_pubsub_topic_square_change(event, context):
    """Background Cloud Function to be triggered by Pub/Sub.
    Args:
         event (dict):  The dictionary with data specific to this type of
         event. The `data` field contains the PubsubMessage message. The
         `attributes` field will contain custom attributes if there are any.
         context (google.cloud.functions.Context): The Cloud Functions event
         metadata. The `event_id` field contains the Pub/Sub message ID. The
         `timestamp` field contains the publish time.
    """
    setup_resources()

    registrations = asyncio.run(microservices.square.api.get_registrations(secrets, square_client))

    logger.log_struct( {
        'event': event,
        'context': context.__dict__,
        'registrations': registrations } )


# pubsub template
# def foolscap_pubsub_topic_xxx(event, context):
#     """Background Cloud Function to be triggered by Pub/Sub.
#     Args:
#          event (dict):  The dictionary with data specific to this type of
#          event. The `data` field contains the PubsubMessage message. The
#          `attributes` field will contain custom attributes if there are any.
#          context (google.cloud.functions.Context): The Cloud Functions event
#          metadata. The `event_id` field contains the Pub/Sub message ID. The
#          `timestamp` field contains the publish time.
#     """
#     import base64

#     log.info("""This Function was triggered by messageId {} published at {}
#     """.format(context.event_id, context.timestamp))

#     microservices.square.api
#     if 'data' in event:
#         name = base64.b64decode(event['data']).decode('utf-8')
#     else:
#         name = 'World'
#     print('Hello {}!'.format(name))

# https://cloud.google.com/functions/docs/calling/cloud-firestore
# gcloud functions deploy FUNCTION_NAME \
#  --runtime RUNTIME
#  --trigger-event providers/cloud.firestore/eventTypes/document.write \
#  --trigger-resource projects/YOUR_PROJECT_ID/databases/(default)/documents/messages/{pushId}


def foolscap_pubsub_topic_bootstrap(event, context):
    setup_resources()
    logger.log_struct( {
        'event': event,
        'conntext': context.__dict__ })

    asyncio.run(microservices.api.bootstrap(secrets, square_client))


# https://cloud.google.com/functions/docs/calling/cloud-firestore
# gcloud functions deploy FUNCTION_NAME \
#  --runtime RUNTIME
#  --trigger-event providers/cloud.firestore/eventTypes/document.write \
#  --trigger-resource projects/YOUR_PROJECT_ID/databases/(default)/documents/messages/{pushId}
# https://cloud.google.com/functions/docs/calling/cloud-firestore
def foolscap_firestore_registration_document_changed(data, context):
    """ Triggered by a change to a Firestore document.
    Args:
        data (dict): The event payload.
        context (google.cloud.functions.Context): Metadata for the event.
    """
    setup_resources()
    trigger_resource = context.resource
    path_parts = context.resource.split('/documents/')[1].split('/')
    service = path_parts[1]
    event = path_parts[3]
    #           0               1      2        3           4              5
    # "foolscap-microservices/square/events/foolscap-2020/registrations/iFW3b8l2DZWQBmzqAtiMGvMF"
    # old_value = data['oldValue']
    # update_mask = data['updateMask']
    # new_value = data['value']
    if event == '{event}': # testing situation. default to current
        event = microservices.event_year.active()[0]
    # call a sync
    logger.log_struct({
        'trigger_resource': trigger_resource })

    asyncio.run(microservices.tito.api.sync_event(secrets, event))
