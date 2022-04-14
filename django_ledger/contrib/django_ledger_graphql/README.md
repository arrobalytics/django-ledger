
# Django ledger Graphql Api

## Usage and installation





``` 
pip install graphene-django
```
``` 
pip install django-graphql-auth
```
Makemigrations
``` 
python manage.py makemigrations
python manage.py migrate
``` 
Runserver
``` 
python manage.py runserver
``` 
make sure you are loged in the main application go to the admin 
site http://127.0.0.1:8000/admin/django_ledger/entitymodel/ choose your 
entity and get your slug name from the entity choosen or

Open new tab and navigate to
``` 
http://127.0.0.1:8000/graphql/
```
paste this to the console and run the query

```
{
  allEntityList{
    slug
    name
  }
```
this will return the current user logged in slug and name, use the slug for other queries (Slugname:String!)
## sample graphql Query
paste this at the graphql console and run the query
```
{
  allEntityList{
    edges{
      node{
        slug
        name
    }
  }
}
```
this will return the current user logged in slug and name, use the slug for other queries (Slugname:String!)
## sample graphql Query
paste this at the graphql console and run the query
```
allCustomers(slugName:"jusper-onderi-ondieki-db23x1y8"){
  edges {
    node {
      customerName
      city
      state
      active
      
    }
  }
}
```

# Query results
```
"allCustomers": {
      "edges": [
        {
          "node": {
            "customerName": "booka",
            "city": "kenya",
            "state": "huj",
            "active": true
          }
        },
        {
          "node": {
            "customerName": "stats",
            "city": "kenya",
            "state": "huj",
            "active": true
          }
        },
        {
          "node": {
            "customerName": "Brooke Weaver",
            "city": "South Michelleborough",
            "state": "WA",
            "active": true
          }
        },
        {
          "node": {
            "customerName": "Tamara Wilson",
            "city": "Castilloport",
            "state": "WV",
            "active": true
          }
        },

        }
      ]
    }
  }
}

```
## Using graphql-auth
Register user
```
mutation {
  register(
    email: "new_user@email.com",
    username: "new_user",
    password1: "dave123456",
    password2: "dave123456",
  ) {
    success,
    errors,
    token,

  }
}
```
Returns a token and a succes message
```
{
  "data": {
    "register": {
      "success": true,
      "errors": null,
      "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6Im5ld191c2VyIiwiZXhwIjoxNjQ5NzY2Nzc4LCJvcmlnSWF0IjoxNjQ5NzY2NDc4fQ.cHaPq8CjQy60ifUawR4Pnyyu_E_SCU2J6CapBK0P8P4"
    }
  }
}
```
for more detail usage visit the documentation
https://django-graphql-auth.readthedocs.io/en/latest/quickstart/