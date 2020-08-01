![alt text](https://us-east-1.linodeobjects.com/django-ledger/logo/django-ledger-logo@2x.png)

### A Book Keeping & Financial Analysis Engine for the Django Framework.

Django Ledger supports:

- Chart of Accounts.
- Financial Statements (Income Statement & Balance Sheets).
- Automatic financial ratio calculations.
- Multiple Entities.
- Self-contained Ledgers.
- Journal Entries & Transactions.
- Financial Activities Support (operational/financial/investing).
- Basic OFX & QFX file import.
- Bills & Invoices with progressible functionality.
- Basic templates.
- Entity administrators & entity manager support.
- Multi-tenancy.
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
- Inventory.
- Per activity reports.
- Tax line mapping.
- Package documentation.
- And a lot more stuff...

## Quick Start
Django Ledger comes with a default CoA ready to use or you could use your own.
Make sure to select the appropriate option when creating new entities.
    
* Install Django Ledger


    pip install django_ledger
    
* Add django_ledger to INSTALLED_APPS


    INSTALLED_APPS = [
        ...
        'django_ledger',
        ...
    ]

* Add URLs to your project:


    urlpatterns = [
        ...
        path('djl/', include('django_ledger.urls', namespace='django_ledger')),
        ...
    ]
  
__This project is actively looking for contributors. Any financial and/or
accounting experience is a big plus.__ \
Want to contribute? Don't hesitate to contact me.