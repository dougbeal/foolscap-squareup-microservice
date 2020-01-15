#!/bin/bash
source bin/activate
python -m microservices.square.main get_registrations 'INFO' $@
python -m microservices.tito.main get_registrations 'INFO' $@
python -m microservices.tito.main sync 'INFO' $@

