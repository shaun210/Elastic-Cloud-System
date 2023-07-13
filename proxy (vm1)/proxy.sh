#!/bin/sh

python3 proxy.py LIGHT &
python3 proxy.py MEDIUM &
python3 proxy.py HEAVY &
