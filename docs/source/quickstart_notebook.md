```python
import os
from datetime import date, datetime
from random import randint, choices, random

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
from django_ledger.models.items import ItemModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.bill import BillModel
from django_ledger.models.estimate import EstimateModel
from django.contrib.auth import get_user_model
from django_ledger.io import roles
```

# Get Your Entity Administrator UserModel


```python
# change this to your preferred django username...
MY_USERNAME = 'ceo_user'
MY_PASSWORD = 'NeverUseMe|VeryInsecure!'
UserModel = get_user_model()

try:
    user_model = UserModel.objects.get(username__exact=MY_USERNAME)
except:
    user_model = UserModel.objects.create(username=MY_USERNAME, password=MY_PASSWORD)
```

# Create an Entity Model


```python
entity_model = EntityModel.create_entity(
    name='One Big Company, LLC',
    admin=user_model,
    use_accrual_method=True,
    fy_start_month=1
)
```


```python
entity_model.slug
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
    coa_name='My QuickStart CoA'
)
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
    coa_name='My Legacy Chart of Accounts'
)
```

# Accounts

## Get All Accounts


```python
coa_qs, coa_map = entity_model.get_all_coa_accounts()
pd.DataFrame(coa_map[default_coa_model].values())
```

### New CoA does not have any accounts yet...


```python
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

## Create Account Model


```python
coa_model, account_model = entity_model.create_account(
    coa_model=another_coa_model,
    account_model_kwargs={
        'code': f'1{str(randint(10000, 99999))}ABC',
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
another_coa_accounts_qs = entity_model.get_coa_accounts(coa_model=another_coa_model)
pd.DataFrame(another_coa_accounts_qs.values())
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
invoice_model = entity_model.create_invoice(
    customer_model='C-0000000006',
    terms=InvoiceModel.TERMS_NET_30
)
```


```python
invoice_model
```

## Add Items to Invoices


```python
invoices_item_models = invoice_model.get_item_model_qs()

# K= number of items...
K = 6

invoice_itemtxs = {
    im.item_number: {
        'unit_cost': round(random() * 10, 2),
        'quantity': round(random() * 100, 2),
        'total_amount': None
    } for im in choices(invoices_item_models, k=K)
}

# Choose operation ITEMIZE_APPEND to append itemtxs...
invoice_itemtxs = invoice_model.migrate_itemtxs(itemtxs=invoice_itemtxs,
                                                commit=True,
                                                operation=InvoiceModel.ITEMIZE_REPLACE)
invoice_itemtxs
```


```python
invoice_model.amount_due
```

# Bills

## Get Bills


```python
bills_qs = entity_model.get_bills()
pd.DataFrame(bills_qs.values())
```

## Create Bill


```python
bill_model = entity_model.create_bill(
    vendor_model='V-0000000002',
    terms=BillModel.TERMS_NET_60
)
```


```python
bill_model
```

## Add Items to Bills


```python
bill_item_models = bill_model.get_item_model_qs()

K = 6

bill_itemtxs = {
    im.item_number: {
        'unit_cost': round(random() * 10, 2),
        'quantity': round(random() * 100, 2),
        'total_amount': None
    } for im in choices(bill_item_models, k=K)
}

# Choose operation ITEMIZE_APPEND to append itemtxs...
bill_itemtxs = bill_model.migrate_itemtxs(itemtxs=bill_itemtxs,
                                          commit=True,
                                          operation=BillModel.ITEMIZE_REPLACE)

bill_itemtxs
```


```python
bill_model.amount_due
```

# Purchase Orders

## Get Purchase Orders


```python
purchase_orders_qs = entity_model.get_purchase_orders()
pd.DataFrame(purchase_orders_qs.values())
```

## Create Purchase Order


```python
po_model = entity_model.create_purchase_order()
```

## Add Items to Purchase Orders


```python
po_item_models = po_model.get_item_model_qs()

K = 6

po_itemtxs = {
    im.item_number: {
        'unit_cost': round(random() * 10, 2),
        'quantity': round(random() * 100, 2),
        'total_amount': None
    } for im in choices(po_item_models, k=K)
}

# Choose operation ITEMIZE_APPEND to append itemtxs...
po_itemtxs = po_model.migrate_itemtxs(itemtxs=po_itemtxs,
                                      commit=True,
                                      operation=EstimateModel.ITEMIZE_REPLACE)

po_itemtxs
```


```python
po_model.po_amount
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
    customer_model='C-0000000009',
    contract_terms=EstimateModel.CONTRACT_TERMS_FIXED
)
```

## Add Items to Estimates


```python
estimate_item_models = estimate_model.get_item_model_qs()

K = 6

estimate_itemtxs = {
    im.item_number: {
        'unit_cost': round(random() * 10, 2),
        'unit_revenue': round(random() * 20, 2),
        'quantity': round(random() * 100, 2),
        'total_amount': None
    } for im in choices(estimate_item_models, k=K)
}

# Choose operation ITEMIZE_APPEND to append itemtxs...
estimate_itemtxs = estimate_model.migrate_itemtxs(itemtxs=estimate_itemtxs,
                                                  commit=True,
                                                  operation=EstimateModel.ITEMIZE_REPLACE)

estimate_itemtxs
```


```python
estimate_model.get_cost_estimate()
```


```python
estimate_model.get_revenue_estimate()
```


```python
estimate_model.get_profit_estimate()
```


```python
estimate_model.get_gross_margin_estimate(as_percent=True)
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

# Items

## Unit of Measures

### Get Unit of Measures


```python
uom_qs = entity_model.get_uom_all()
pd.DataFrame(uom_qs.values())
```

### Create a UOM


```python
uom_model_ft = entity_model.create_uom(
    name='Linear Feet',
    unit_abbr='lin-ft'
)
```

### Get Some UoMs


```python
uom_model_unit = uom_qs.get(unit_abbr__exact='unit')
uom_model_man_hr = uom_qs.get(unit_abbr__exact='man-hour')
```

## Expenses

### Get Expense Items


```python
expenses_qs = entity_model.get_items_expenses()
pd.DataFrame(expenses_qs.values())
```

### Create Expense Item


```python
expense_item_model = entity_model.create_item_expense(
    name='Premium Pencils',
    uom_model=uom_model_unit,
    expense_type=ItemModel.ITEM_TYPE_MATERIAL
)
```


```python
expense_item_model.is_expense()
```

## Services

### Get Service Items


```python
services_qs = entity_model.get_items_services()
pd.DataFrame(services_qs.values())
```

### Create Service Item


```python
service_model = entity_model.create_item_service(
    name='Yoga Class',
    uom_model=uom_model_man_hr
)
```


```python
service_model.is_service()
```

## Products

### Get Product Items


```python
products_qs = entity_model.get_items_products()
pd.DataFrame(products_qs.values())
```

### Create Product Items


```python
product_model = entity_model.create_item_product(
    name='1/2" Premium PVC Pipe',
    uom_model=uom_model_ft,
    item_type=ItemModel.ITEM_TYPE_MATERIAL
)
```


```python
product_model.is_product()
```

## Inventory

### Get Inventory Items


```python
inventory_qs = entity_model.get_items_inventory()
pd.DataFrame(inventory_qs.values())
```

### Create Inventory Items


```python
inventory_model = entity_model.create_item_inventory(
    name='A Home to Flip!',
    uom_model=uom_model_unit,
    item_type=ItemModel.ITEM_TYPE_LUMP_SUM
)
```


```python
inventory_model.is_inventory()
```

# Financial Statements

## Balance Sheet


```python
bs_report = entity_model.get_balance_sheet_statement(
    to_date=date(2022, 12, 31),
    save_pdf=True,
    filepath='./'
)
# save_pdf=True saves the PDF report in the project's BASE_DIR.
# filename and filepath may also be specified...
# will raise not implemented error if PDF support is not enabled...
```

### Balance Sheet Statement Raw Data


```python
bs_report.get_report_data()
```

## Income Statement


```python
ic_report = entity_model.get_income_statement(
    from_date=date(2022, 1, 1),
    to_date=date(2022, 12, 31),
    save_pdf=True,
    filepath='./'
)
# save_pdf=True saves the PDF report in the project's BASE_DIR.
# filename and filepath may also be specified...
# will raise not implemented error if PDF support is not enabled...
```

### Income Statement Raw Data


```python
ic_report.get_report_data()
```

## Cash Flow Statement


```python
cf_report = entity_model.get_cash_flow_statement(
    from_date=date(2022, 1, 1),
    to_date=date(2022, 12, 31),
    save_pdf=True,
    filepath='./'
)
# save_pdf=True saves the PDF report in the project's BASE_DIR.
# filename and filepath may also be specified...
```

### Cash Flow Statement Raw Data


```python
cf_report.get_report_data()
```

## All Financial Statements Data in a single Call


```python
reports = entity_model.get_financial_statements(
    user_model=user_model,
    from_date=date(2022, 1, 1),
    to_date=date(2022, 12, 31),
    save_pdf=True,
    filepath='./'
)
# save_pdf=True saves the PDF report in the project's BASE_DIR.
# filename and filepath may also be specified...
```


```python
reports.balance_sheet_statement.get_report_data()
```


```python
reports.income_statement.get_report_data()
```


```python
reports.cash_flow_statement.get_report_data()
```


```python

```
