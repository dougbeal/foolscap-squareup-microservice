# setup
- create venv
- 

# Google Cloud 
## setup
- https://cloud.google.com/functions/docs/quickstart 
- create cloud project called "foolscap microservices"
- brew cask install google-cloud-sdk
- gcloud init
- select "foolscap microservices"


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
