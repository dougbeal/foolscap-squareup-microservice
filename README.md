# setup, local development
- create venv
- https://firebase.google.com/docs/functions/local-emulator
## firebase emulation
- gcloud beta emulators firestore start


# Google Cloud
## setup
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
- $ gcloud beta secrets create secrets --replication-policy=automatic --data-file=secrets.yaml


   .
   .......... .....    .  .   . .............
   .               .............       .. ..
   .                                       .
    .    square webhook                    .
    .    in person sale                   .
     .                                    .
     .                          .. . . ....
     .         ... ..... ... .
     ... .... .
    ..                             .....
    .  ... .  . . .  . . . . ... ..    .
     .                                 .
     .  tito webook                     .
     .  online sale                     .
     .                                  .
     ..... .. .          . ........ .....
                ..  .. .
