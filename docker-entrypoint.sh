#!/bin/sh
set -e

uv run --no-dev python manage.py migrate --noinput

exec "$@"
