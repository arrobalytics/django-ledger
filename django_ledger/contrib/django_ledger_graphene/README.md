
# Django ledger Graphql Api

## Usage and installation
Install Required Packages

First, install the necessary packages:
``` 
pip install graphene-django
```
``` 
pip install django-oauth-toolkit
```
Enable Graphql by navigating to ./django_ledger/settings.py
```
 DJANGO_LEDGER_GRAPHQL_SUPPORT_ENABLED = True 
```
Makemigrations
``` 
python manage.py makemigrations
python manage.py migrate
```
Start the Django development server:
``` 
python manage.py runserver
```
on the admin site ensure to add an Application with the fields 
```
client type: confidential
Authorization grant type:  Resource owner password-based 
```

Use Postman or Thunder Client to make a POST request to obtain an access token. Send a request to the following URL:

```

http://127.0.0.1:8000/api/v1/o/token/
```
Include the following JSON body in your request:
```
{
    "username": "eric",
    "password": "eric",
    "client_id": "cXFFgnvWhWiZDofGkwiwUBdfuxfNnLsmBtAVsVXv",
    "client_secret": "dave101",
    "grant_type": "password"
}
```
If the request is successful, you will receive a response like this:
```
{
    "access_token": "YPMh29n648qpahgtOjrDHMDy5bt81e",
    "expires_in": 36000,
    "token_type": "Bearer",
    "scope": "read write",
    "refresh_token": "huBiNKw9IhtuYPKVNR9i4WnQesMqEl"
}
```
Now you can use the access token to authenticate your GraphQL requests.

