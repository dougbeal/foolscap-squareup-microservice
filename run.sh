#!/bin/bash
source bin/activate
python squarecli.py run_get_registrations
python titocli.py run_get_registrations
find . -name \*.py.json -depth 1 -exec python3 -m json.tool {} {}.pp.json \;
python titocli.py run_sync

