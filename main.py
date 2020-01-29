from pprint import pformat
import os
import asyncio
import json

if os.getenv('GAE_ENV', '').startswith('standard'):
    import google.cloud.logging
    from google.cloud import firestore

    # Instantiates a client
    client = google.cloud.logging.Client()

    # Connects the logger to the root logging handler; by default this captures
    # all logs at INFO level and higher
    client.setup_logging()

import logging
log = logging.getLogger()

def foolscap_square_webhook(request):
    log.info("%s %s", request, request.get_data())

def foolscap_tito_webhook(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
    Returns:
        <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
    """
    log.info("%s %s", request, request.get_data())
    request_json = request.get_json(silent=True)
    request_args = request.args

    if '_type' in request_json and request_json['_type'] == 'registration':
        asyncio.run(api.write_tito_registration(request_json))

# https://cloud.google.com/functions/docs/calling/cloud-firestore
# gcloud functions deploy FUNCTION_NAME \
#  --runtime RUNTIME
#  --trigger-event providers/cloud.firestore/eventTypes/document.write \
#  --trigger-resource projects/YOUR_PROJECT_ID/databases/(default)/documents/messages/{pushId}

def firetore_registration_document_changed(data, context):
    """ Triggered by a change to a Firestore document.
    Args:
        data (dict): The event payload.
        context (google.cloud.functions.Context): Metadata for the event.
    """
    trigger_resource = context.resource

    log.info('Function triggered by change to: %s' % trigger_resource)

    log.info('\nOld value:')
    log.info(json.dumps(data["oldValue"]))

    log.info('\nNew value:')
    log.info(json.dumps(data["value"]))
