![django ledger logo](https://us-east-1.linodeobjects.com/django-ledger/logo/django-ledger-logo@2x.png)

### A Bookkeeping & Financial Analysis Engine for the Django Framework.

Django Ledger supports:

- Chart of Accounts.
- Financial Statements (Income Statement & Balance Sheets).
- Automatic financial ratio & insight calculations.
- Multi tenancy (multiple users/clients).
- Hierarchical entity management (for consolidated financial statements - v0.9).
- Self-contained Ledgers, Journal Entries & Transactions.
- Basic OFX & QFX file import.
- Bills & Invoices with optional _accruable_ functionality.
- Basic navigational templates.
- Entity administration & entity manager support.
- Items, lists & inventory management.
- Bank Accounts.

__WARNING__: Currently this project is under active development, it is not stable and is not recommended for production
environments. Due to its high complexity, breaking changes may occur in future releases and migration backwards 
compatibility may not be preserved until the first __stable__ release. The author is actively working to provide a 
stable release as soon as possible and to incorporate the following functionality:

## High Level Road Map

- Cash flow statement.
- Entity Nesting and Corporate Structures.
- Tax line mapping.
- Package documentation.
- Collaborators & Permissions.
- API Implementation.
- Unit Tests & Behavior Driven Development Tests.
- And a lot more stuff...

For more details please check our full
v1.0 [Roadmap](https://github.com/arrobalytics/django-ledger/blob/develop/ROADMAP.md).

# Want to contribute?

__This project is actively looking for contributors. Any financial and/or accounting experience is a big plus.__
If you have prior accounting experience and want to contribute, don't hesitate to contact me.
See __[contribution guidelines](https://github.com/arrobalytics/django-ledger/blob/develop/Contribute.md)__.

## Quick Start

Django Ledger comes with a default CoA ready to use or you could use your own. Make sure to select the appropriate
option when creating new entities.

* Install Django Ledger

```shell script
pip install git+https://github.com/arrobalytics/django-ledger.git
```

To install Django Virtual Environment
```pip install pipenv```

* Or with pipenv:

```shell script
pipenv install git+https://github.com/arrobalytics/django-ledger.git
```

* Add django_ledger to INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...,
    'django_ledger',
    ...,
]
```

* Add URLs to your project:

```python
from django.urls import include, path

urlpatterns = [
    ...,
    path('ledger/', include('django_ledger.urls', namespace='django_ledger')),
    ...,
]
```

# Screenshots

![django ledger entity dashboard](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_entity_dashboard.png)
![django ledger balance sheet](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_income_statement.png)
![django ledger income statement](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_balance_sheet.png)
![django ledger bill](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_bill.png)
![django ledger invoice](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_invoice.png)
