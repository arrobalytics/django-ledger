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
- Bills & Invoices with progressible functionality.
- Basic navigational templates.
- Entity administration & entity manager support.
- Bank Accounts.
- Extensible API & Object Oriented Accounting.


Currently this project is under active development and is not recommended for production environments.
Breaking changes may occur in future releases.
The author is actively working to provide a stable release and to incorporate
the following functionality:

## High Level Road Map
- Basic navigational views & template tags.
- Basic entity insights.
- Cash flow statement.
- Inventory Management.
- Tax line mapping.
- Package documentation.
- And a lot more stuff...

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
    path('djl/', include('django_ledger.urls', namespace='django_ledger')),
    ...,
]
```


# Screenshoots

![django ledger screenshoot](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_screenshot.png)

  
__This project is actively looking for contributors. Any financial and/or
accounting experience is a big plus.__ \
If you have prior accounting experience and want to contribute, 
don't hesitate to contact me.