
# Django ledger Graphql Api

## Usage and installation





``` 
pip install graphene-django
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
  allAccounts (slugName: "jusper-hsy7"){
    name
    NoneCashAccount{
      terms
    }
    balanceType
  }
  allBankAccountList (slugName: "jusper-hsy7"){
    name
  }
  allCustomers (slugName: "jusper-hsy7"){
    customerName
    phone
    city
  }
}
```

# Query results
```
{
  "data": {
    "allAccounts": [
      {
        "name": "Cash",
        "NoneCashAccount": [
          {
            "terms": "NET_30"
          },
          {
            "terms": "NET_30"
          },
          {
            "terms": "NET_60"
          },
          {
            "terms": "NET_90"
          },
          {
            "terms": "ON_RECEIPT"
          }
        ]
      },
      {
        "name": "Short Term Investments",
        "NoneCashAccount": []
      },
      {
        "name": "Buildings",
        "NoneCashAccount": []
      },
      {
        "name": "Vehicles",
        "NoneCashAccount": []
      },
      {
        "name": "Less: Vehicles Accumulated Depreciation",
        "NoneCashAccount": []
      },
      {
        "name": "PPE Unrealized Gains/Losses",
        "NoneCashAccount": []
      },
      {
        "name": "Accounts Payable",
        "NoneCashAccount": []
      },
      {
        "name": "Wages Payable",
        "NoneCashAccount": []
      },
      {
        "name": "Interest Payable",
        "NoneCashAccount": []
      },
      {
        "name": "Available for Sale",
        "NoneCashAccount": []
      },
      {
        "name": "PPE Unrealized Gains/Losses",
        "NoneCashAccount": []
      },
      {
        "name": "Electricity",
        "NoneCashAccount": []
      },
      {
        "name": "Property Management",
        "NoneCashAccount": []
      },
      {
        "name": "Vacancy",
        "NoneCashAccount": []
      },
      {
        "name": "Misc. Revenue",
        "NoneCashAccount": []
      },
      {
        "name": "Misc. Expense",
        "NoneCashAccount": []
      }
    ],
    "allBankAccountList": [
      {
        "name": "JUSPER ONDERI ONDIEKI Checking Account"
      },
      {
        "name": "JUSPER ONDERI ONDIEKI Savings Account"
      }
    ],
    "allCustomers": [
      {
        "customerName": "Wendy Jordan"
      },
      {
        "customerName": "Alicia Miller"
      },
      {
        "customerName": "Brooke Weaver"
      }
    ]
  }
}
