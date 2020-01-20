![alt text](https://storage.googleapis.com/djetler/logo/v1/djetler-logo%402x.png)

### A bookkeeping & financial analysis engine for the Django Framework.

Djetler supports:

- Chart of Accounts.
- Financial Statements (Income Statement & Balance Sheets)
- Entities (LLC, Corps, etc.)
- General/Individual Ledgers.
- Journal Entries & Transactions.
- Financial Activities Support (Operational/Financial/Investing).
- Entity/Account/Journal Entries 

Currently this project is under active development and is not recommended for production environments.
Breaking changes may occur in future releases.
The author is actively working to provide a stable release and to incorporate
the following functionality:

## High Level Road Map
- Basic navigational views & template tags.
- Basic entity insights.
- Cash flow statement.
- Invoicing.
- Inventory.
- Per activity reports.
- Financial analysis ratios.
- Tax line mapping.
- What if scenarios.
- Account level forecasting/trends.
- Package documentation.
- And a lot more stuff...

## Quick Start
In order to start using Django Ledger you must be logged in first.

Django Ledger comes with a default CoA ready to use or you could use your own.
Make sure to select the appropriate option when creating new entities.

* Install Dependencies


    pip install django-mptt
    
    
   or if using Pipenv
    
    pipenv install
    
* Add mptt & django_ledger to INSTALLED_APPS


    INSTALLED_APPS = [
        ...
        'mptt',
        'django_ledger',
        ...
    ]

* Add URLs to your project:


    urlpatterns = [
        ...
        path('', include('django_ledger.urls')),
        ...
    ]
    
__Want to contribute? Don't hesitate to contact me.__