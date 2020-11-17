![django ledger logo](https://us-east-1.linodeobjects.com/django-ledger/logo/django-ledger-logo@2x.png)

### A Bookkeeping & Financial Analysis Engine for the Django Framework.

Django Ledger supports:

- Chart of Accounts.
- Financial Statements (Income Statement & Balance Sheets).
- Automatic financial ratio & insight calculations.
- Multi tenancy.
- Hierarchical entity management. 
- Self-contained Ledgers, Journal Entries & Transactions.
- Financial Activities Support (operational/financial/investing).
- Basic OFX & QFX file import.
- Bills & Invoices with optional progressible functionality.
- Basic navigational templates.
- Entity administration & entity manager support.
- Bank Accounts.

__WARNING__: Currently this project is under active development and is not recommended for production
environments. Breaking changes may occur in future releases.
The author is actively working to provide a stable release as soon as possible and to incorporate
the following functionality:

## High Level Road Map
- Cash flow statement.
- Inventory Management.
- Tax line mapping.
- Package documentation.
- Collaborators & Permissions.
- Extensible API & Object Oriented Accounting.
- Unit Tests & Behavioral Driven Tests.
- And a lot more stuff...

# Want to contribute?
__This project is actively looking for contributors. Any financial and/or
accounting experience is a big plus.__
If you have prior accounting experience and want to contribute, 
don't hesitate to contact me.

## Quick Start
Django Ledger comes with a default CoA ready to use or you could use your own.
Make sure to select the appropriate option when creating new entities.
    
* Install Django Ledger

```shell script
pip install git+https://github.com/arrobalytics/django-ledger.git
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
urlpatterns = [
    ...,
    path('ledger/', include('django_ledger.urls', namespace='django_ledger')),
    ...,
]
```


# Screenshoots

![django ledger entity dashboard](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_entity_dashboard.png)
![django ledger balance sheet](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_income_statement.png)
![django ledger income statement](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_balance_sheet.png)
![django ledger bill](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_bill.png)
![django ledger invoice](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_invoice.png)