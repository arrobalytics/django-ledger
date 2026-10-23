#!/bin/sh

echo "Going to run migrations"
uv run python manage.py migrate

echo "Going to run django server"
uv run python manage.py runserver 0.0.0.0:8000