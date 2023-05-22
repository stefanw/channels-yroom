#!/bin/sh

set -ex

docker compose up -d

playwright install
pytest example/tests/test.py

docker compose down
