#!/usr/bin/env bash
set -o errexit

# Run migrations
python manage.py migrate --noinput

# Start gunicorn
gunicorn finance_app.wsgi:application -c gunicorn_config.py