```python
import os
from datetime import date, datetime
from random import randint

import django

# for easier visualization it is recommended to use pandas to render data...
# if pandas is not installed, you may install it with this command: pip install -U pandas
# pandas is not a dependecy of django_ledger...
import pandas as pd

# Set your django settings module if needed...
os.environ['DJANGO_SETTINGS_MODULE'] = 'dev_env.settings'

# if using jupyter notebook need to set DJANGO_ALLOW_ASYNC_UNSAFE as "true"
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

# change your working directory as needed...
os.chdir('../')

django.setup()

from django_ledger.models.entity import EntityModel
from django.contrib.auth import get_user_model
from django_ledger.io import roles
```

# Get Your Entity Administrator UserModel


```python
# change this to your preferred django username...
MY_USERNAME = 'elarroba'
UserModel = get_user_model()
user_model = UserModel.objects.get(username__exact=MY_USERNAME)
```

# Create an Entity Model


```python
entity_model = EntityModel(
    name='One Big Company, LLC',
    admin=user_model,
)
entity_model.clean()
entity_model = EntityModel.add_root(instance=entity_model)
```

# Chart of Accounts

## Create a Default Chart of Accounts


```python
entity_model.has_default_coa()
```


```python
default_coa_model = entity_model.create_chart_of_accounts(
    assign_as_default=True, 
    commit=True, 
    coa_name='My QuickStart CoA')
```


```python
default_coa_model
```

# Populate Entity with Random Data

### Define a Start Date for Transactions


```python
START_DATE = date(year=2022, month=10, day=1)
```


```python
entity_model.populate_random_data(start_date=START_DATE)
```

### EntityModel has now a Default Chart of Accounts


```python
entity_model.has_default_coa()
```


```python
default_coa_model = entity_model.get_default_coa()
```

# Chart of Accounts (CoA)

## Django Ledger support multiple chart of accounts.


```python
another_coa_model = entity_model.create_chart_of_accounts(
    assign_as_default=False, 
    commit=True, 
    coa_name='My Legacy Chart of Accounts')
```

# Accounts

## Get All Accounts


```python
coa_qs, coa_map = entity_model.get_all_coa_accounts()
pd.DataFrame(coa_map[default_coa_model].values())
```


```python
# new CoA does not have any accounts yet...
pd.DataFrame(coa_map[another_coa_model].values())
```

## Get Default CoA Accounts


```python
default_coa_accounts_qs = entity_model.get_default_coa_accounts()
pd.DataFrame(default_coa_accounts_qs.values())
```

## Get CoA Accounts by CoA Model


```python
coa_accounts_by_coa_model_qs = entity_model.get_coa_accounts(coa_model=default_coa_model)
pd.DataFrame(coa_accounts_by_coa_model_qs.values())
```

## Get CoA Accounts by CoA Model UUID


```python
coa_accounts_by_coa_uuid_qs = entity_model.get_coa_accounts(coa_model=default_coa_model.uuid)
pd.DataFrame(coa_accounts_by_coa_uuid_qs.values())
```

## Get CoA Accounts by CoA Model Slug


```python
coa_accounts_by_coa_slug_qs = entity_model.get_coa_accounts(coa_model=default_coa_model.slug)
pd.DataFrame(coa_accounts_by_coa_slug_qs.values())
```

## Get Accounts With Codes and CoA Model


```python
coa_accounts_by_codes_qs = entity_model.get_accounts_with_codes(code_list=['1010', '1050'])
pd.DataFrame(coa_accounts_by_codes_qs.values())
```


```python
coa_accounts_by_codes_qs = entity_model.get_accounts_with_codes(code_list=['1010', '1050'], 
                                                                coa_model=another_coa_model)
pd.DataFrame(coa_accounts_by_codes_qs.values())
```

## Create Account Model


```python
coa_model, account_model = entity_model.create_account(
    coa_model=another_coa_model,
    account_model_kwargs={
        'code': f'1{str(randint(10000,99999))}ABC',
        'role': roles.ASSET_CA_INVENTORY,
        'name': 'A cool account created from the EntityModel API!',
        'balance_type': roles.DEBIT,
        'active': True
    })
```


```python
account_model
```


```python
given_coa_accounts_qs = entity_model.get_coa_accounts(coa_model=another_coa_model)
pd.DataFrame(given_coa_accounts_qs.values())
```

# Customers

## Get Customers


```python
customer_qs = entity_model.get_customers()
pd.DataFrame(customer_qs.values())
```

## Create Customers


```python
customer_model = entity_model.create_customer(customer_model_kwargs={
    'customer_name': 'Mr. Big',
    'description': 'A great paying customer!',
})
```

# Vendors

## Get Vendors


```python
vendor_qs = entity_model.get_vendors()
pd.DataFrame(vendor_qs.values())
```

## Create Vendor


```python
vendor_model = entity_model.create_vendor(vendor_model_kwargs={
    'vendor_name': 'ACME LLC',
    'description': 'A Reliable Vendor!'
})
```

# Invoices

## Get Invoices


```python
invoices_qs = entity_model.get_invoices()
pd.DataFrame(invoices_qs.values())
```

## Create Invoice


```python
invoice_model = entity_model.create_invoice(customer_model='C-0000000006')
```

# Bills

## Get Bills


```python
bills_qs = entity_model.get_bills()
pd.DataFrame(bills_qs.values())
```

## Create Bill


```python
bill_model = entity_model.create_bill(vendor_model='V-0000000002')
```

# Purchase Orders

## Get Purchase Orders


```python
purchase_orders_qs = entity_model.get_purchase_orders()
pd.DataFrame(purchase_orders_qs.values())
```

## Create Purchase Order


```python
purchase_order = entity_model.create_purchase_order()
```

# Estimates/Contracts

## Get Estimates/Contracts


```python
estimates_qs = entity_model.get_estimates()
pd.DataFrame(estimates_qs.values())
```

## Create Estimate


```python
estimate_model = entity_model.create_estimate(
    estimate_title='A quote for new potential customer!', 
    customer_model='C-0000000009'
)
```

# Bank Accounts

## Get Bank Accounts


```python
bank_accounts_qs = entity_model.get_bank_accounts()
pd.DataFrame(bank_accounts_qs.values())
```

## Create Bank Account


```python
bank_account_model = entity_model.create_bank_account(name='A big bank account!',
                                                      account_type='checking')
```

# Financial Statements

## Balance Sheet


```python
txs_qs, io_digest = entity_model.get_balance_sheet(
    user_model=user_model,
    to_date=date(2022,12,31)
)
```

### The digest object contains all relevant financial data for the requested period
#### The balance sheet information is summarized in its own namespace


```python
io_digest['tx_digest']['balance_sheet']
```

## Income Statement


```python
txs_qs, io_digest = entity_model.get_income_statement(
    user_model=user_model,
    from_date=date(2022,1,1),
    to_date=date(2022,12,31)
)
```

### The digest object contains all relevant financial data for the requested period
#### The income statement information is summarized in its own namespace


```python
io_digest['tx_digest']['income_statement']
```

## Cash Flow Statement


```python
txs_qs, io_digest = entity_model.get_cash_flow_statement(
    user_model=user_model,
    from_date=date(2022,1,1),
    to_date=date(2022,12,31)
)
```

### The digest object contains all relevant financial data for the requested period
#### The cash flow statement information is summarized in its own namespace


```python
io_digest['tx_digest']['cash_flow_statement']
```

## All Financial Statements in a single call


```python
txs_qs, io_digest = entity_model.get_financial_statements(
    user_model=user_model,
    from_date=date(2022,1,1),
    to_date=date(2022,12,31)
)
```

### The digest object contains all relevant financial data for the requested period
#### All financial statements are summarized in its own namespace


```python
io_digest['tx_digest']['balance_sheet']
```


```python
io_digest['tx_digest']['income_statement']
```


```python
io_digest['tx_digest']['cash_flow_statement']
```
