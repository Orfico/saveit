#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Collectstatic (non richiede DB)
python manage.py collectstatic --noinput