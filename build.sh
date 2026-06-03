#!/usr/bin/env bash
# exit on error
set -o errexit

# Idinagdag ang --no-cache-dir para i-clear ang conflict sa server
pip install --no-cache-dir -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate