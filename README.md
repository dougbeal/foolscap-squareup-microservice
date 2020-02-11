#!/usr/bin/env mdsh
# setup, local development
```
brew install python3 
python3.8 -m venv .  # create virtual environment
source bin/activate
pip install -r requirements_dev.txt
```
- https://cloud.google.com/sdk/install
- https://cloud.google.com/sdk/docs/downloads-interactive
- https://firebase.google.com/docs/functions/local-emulator

```
glcoud init
# select foolscap-microservices project (account dougbeal)
gcloud components install beta
# need java runtime fore firestore emulator
brew cask install java 
```

# running local enviornemnt (assumes venv is activated)
```
gcloud beta emulators firestore start --host-port localhost:8582
```
# run entire pipeline, with mocked requets.post and requests.patch
```
./run.sh
```
# run pipeline, send changes to tito
``` 
./run.sh --production
```

# run sync with DEBUG log level
```
python -m microservices.tito.main sync 'DEBUG'
```
## firebase emulation
- 

# example run, use real data but don't make any changes
```
. bin/activate
./run.sh  --mode-production-dry-run

```
# Google Cloud
## setup
# default region - multiregion nam5 due to firestore restrictions
```
gcloud compute project-info add-metadata --metadata google-compute-default-region=nam5
```
- https://cloud.google.com/functions/docs/quickstart
- create cloud project called "foolscap microservices"
- brew cask install google-cloud-sdk
- gcloud init
- select "foolscap microservices"
- create cloud firestore native db in nam5 region (multiregion)
### firebase
- firebase login
### HTTP Triggers https://cloud.google.com/functions/docs/calling/http
- use Flask
#### tito webhook
- registration.completed
#### square webhook
## deploy functions from source https://cloud.google.com/functions/docs/deploying/rep

- gcloud beta functions deploy function-123 --source https://source.developers.google.com/projects/project-123/repos/default/moveable-alises/master --entry-point function-123 --trigger-http
- `https://source.developers.google.com/projects/*/repos/*/moveable-aliases/*/paths/*`

# deloy helper functions
```
function deploy_http_function {
    PROJECT_ID=foolscap-microservices 
    REPOSITORY_NAME=github_dougbeal_foolscap-squareup-microservice 
    BRANCH=master 
    FUNCTION_NAME=$1
    gcloud functions deploy $FUNCTION_NAME \
      --allow-unauthenticated \
      --source https://source.developers.google.com/projects/$PROJECT_ID/repos/$REPOSITORY_NAME/moveable-aliases/$BRANCH/paths// \
      --runtime python37 \
      --entry-point $FUNCTION_NAME \
      --trigger-http
}

function deploy_firestore_function {
    PROJECT_ID=foolscap-microservices 
    REPOSITORY_NAME=github_dougbeal_foolscap-squareup-microservice 
    BRANCH=master 
    FUNCTION_NAME=$1
    DOCUMENT_PATH=$2
    gcloud functions deploy $FUNCTION_NAME \
      --source https://source.developers.google.com/projects/$PROJECT_ID/repos/$REPOSITORY_NAME/moveable-aliases/$BRANCH/paths// \
      --runtime python37 \
      --entry-point $FUNCTION_NAME \
      --trigger-event providers/cloud.firestore/eventTypes/document.write \
      --trigger-resource "projects/$PROJECT_ID/databases/(default)/documents/$DOCUMENT_PATH"
}

function deploy_pubsub_function {
    PROJECT_ID=foolscap-microservices 
    REPOSITORY_NAME=github_dougbeal_foolscap-squareup-microservice 
    BRANCH=master 
    FUNCTION_NAME=$1
    TOPIC=$2
    gcloud functions deploy $FUNCTION_NAME \
      --source https://source.developers.google.com/projects/$PROJECT_ID/repos/$REPOSITORY_NAME/moveable-aliases/$BRANCH/paths// \
      --runtime python37 \
      --entry-point $FUNCTION_NAME \
      --trigger-topic $TOPIC
}
```
```
(deploy_http_function foolscap_square_webhook)&
(deploy_http_function foolscap_tito_webhook)&


(deploy_pubsub_function foolscap_pubsub_topic_square_change square.change)&
(deploy_pubsub_function foolscap_pubsub_topic_bootstrap bootstrap)&  

(deploy_firestore_function foolscap_firestore_registration_document_changed "foolscap-microservices/{service}/events/{event}/registrations/{registration}")&


  
```

# add dependencies, account for packages already in requirements*.txt
```
pip  freeze -r requirements.txt -r requirements_dev.txt
```

Task or PubSub?a

- square webhook
TRIGGER: httpTrigger
INPUT: http payload
OUTPUT: task payment_id
PAYMENT_UPDATED notifications also include an entity_id, which is a payment ID that can be used to look up more information.
For Connect API applications created after February 16, 2016, use location_id and entity_id to identify and retrieve transactions associated with a webhook event.
https://github.com/square/connect-api-examples/blob/master/connect-examples/v1/python/webhooks.py
https://developer.squareup.com/reference/square/payments-api/get-payment -> order_id
looks easier to just grab everything
- httptrigger
- Function: square webhook handler
- Task, square_changed [include payment id for future flexibility] (just retrive everything?, or changed item?)

- tito webhook [includes changed information]
TRIGGER: httpTrigger
INPUT: http payload
OUTPUT: task http payload
- httptrigger
- Function: tito webhook handler
- Task, tito_changed [include webhook payload for future flex] or Firestore document (just retrive everything?, or changed item?)
 

- Task, square_changed, task (square get reg)
TRIGGER: Task(queue
INPUT: 
OUTPUT: firestore json [square registrations]
- Function: square.get_registrations
- http requests
- Firestore documents

- Task, tito_changed, task (tito get reg)
TRIGGER: Task
INPUT: 
OUTPUT: firestore json [tito registrations]
- Function: tito.get_registrations
- http requests
- Firestore documents

- task or firestore change (sync)
TRIGGER:
INPUT: firestore.square.reg, firestore.tito.reg
OUTPUT: Task(new_tito_reg, payload), 
- both square and tito get_reg should be complete OR webhook trigger
- POST: send new registrations to tito
- task: number

- task new_tito_reg
TRIGGER: Task
INPUT: registration data
OUTPUT:


- task: re/number
TRIGGER: Task
INPUT: registration data
OUTPUT:
- number tito tickets (order by square reg date or tito web reg)
- update number questions on tickets in 





# google cloud firestore
```
gcloud alpha firestore databases create --region=us-central
```

# TODO
## for production
- turn caching off
- consume from queue
- produce to queue
- google logging?
### secrets
- supply secrets as env variables https://cloud.google.com/functions/docs/env-var
- Google Secret Manager? https://cloud.google.com/secret-manager/docs/quickstart-secret-manager-console
- https://cloud.google.com/secret-manager/docs/quickstart-secret-manager-api
- https://dev.to/googlecloud/using-secrets-in-google-cloud-functions-5aem
```
gcloud beta secrets create secrets --replication-policy=automatic --data-file=secrets.yaml
gcloud beta secrets add-iam-policy-binding secrets \
    --role roles/secretmanager.secretAccessor \
    --member serviceAccount:foolscap-microservices@appspot.gserviceaccount.com
```


# Testing
```
python -m unittest discover test
nose2 --debugger test.test_main.TestTito
# test
curl -X POST "https://nam3-foolscap-microservices.cloudfunctions.net/$FUNCTION_NAME" -H "Content-Type:application/json" --data '{"name":"Keyboard Cat"}'
gcloud pubsub topics publish square.change  --message "message"
```

TODO: rename repo to foolscap-microservices
