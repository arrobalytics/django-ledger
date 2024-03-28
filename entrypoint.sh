#!/bin/sh

echo "Going to install django"
pipenv install django

echo "Going to install dependencies"
pipenv install

echo "Going to run migrations"
pipenv run python manage.py migrate

echo "Going to run django server"
pipenv run python manage.py runserver 0.0.0.0:8000