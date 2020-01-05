#!/bin/bash
source bin/activate
python -m microservices.square.main get_registrations
python -m microservices.tito.main get_registrations
find . -name \*.py.json -depth 2 -exec python3 -m json.tool {} {}.pp.json \;
python -m microservices.tito.main sync

