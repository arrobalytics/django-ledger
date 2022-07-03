![django ledger logo](https://us-east-1.linodeobjects.com/django-ledger/logo/django-ledger-logo@2x.png)

### A Bookkeeping & Financial Analysis Engine for the Django Framework.

The __Django Ledger Project__ is led and maintained by Miguel Sanda aiming to provide an open source financial
engine to power financially driven applications using Python and the Django Framework. Unfortunately
due to its complexity we cannot offer a stable release until all features on the
[Roadmap](https://github.com/arrobalytics/django-ledger/blob/develop/ROADMAP.md) has been implemented.

Finance and Accounting is a complicated subject. Django Ledger is different from other Django projects 
as it aims to provide a developer-friendly accounting engine while providing a reliable and extensible API. 
This project in particular, not only requires Python AND Django programming experience, but also finance and 
accounting experience.

Due to time limitations, the developer is focusing on the development of new features. \
__This project can greatly benefit from contributions towards Documentation and Unit Tests.__

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

# Roadmap to Version 1.0 Stable

### ~~Version 0.4~~ *completed*

* __0.4.0__: Items, resources and & lists for bills & invoices itemization:
* __0.4.0__: Enhance and optimize Django Ledger the random data generation functionality to properly populate relevant
  random data for testing.
* __0.4.1__: Entity internal organizations, department, branches, etc.
* __0.4.2__: Custom Accounting Periods.
* __0.4.3__: Purchase Order Model implementation.
* Bugfixes & UI/UX Enhancements.

### Version 0.5

More details available in the [Django Ledger v0.5 Page](https://www.arrobalytics.com/blog/2021/12/07/django-ledger-v05/).

* __0.5.0__: Inventory tracking.
  * Average Cost.
* __0.5.1__: Customer estimates & contract tracking.
  * Link Estimate/PO/Bill/Invoice workflow.
  * Journal Entry (or trial balance) import.
* __0.5.2__: Cash flow statement.
* __0.5.3__: Closing entries, snapshots & trial balance import.
* __0.5.4__: Testing framework implementation that will include:
  * Unit tests using the [Built-in Django](https://docs.djangoproject.com/en/3.1/topics/testing/) unit test modules.
  * Behavioral Driven Testing using the [behave](https://behave.readthedocs.io/en/latest/) library.
  * __Need help!!!! If you want to contribute PLEASE ADD UNIT TESTS!!!__
* Start creating basic package documentation via [Sphinx](https://www.sphinx-doc.org/en/master/)
    * Document code and functions within code base.
    * Generate HTML documentation.
* Work with Accountants, Subject Experts and Developers to define an initial list of Unit Tests to validate output __(
  help needed!)__.
* Update package and code documentation.
* Bugfixes & UI/UX Enhancements.

### Version 0.6

* Credit Line Models.
* Time tracking.
* Transaction tagging.
* Update package and code documentation.
* Bugfixes & UI/UX Enhancements.

### Version 0.7

* Currency Models implementation as a way to define EntityModel default currency.
* Produce financial statements in different currencies.
* Update package and code documentation.
* Bugfixes & UI/UX Enhancements.

### Version 0.8

* User roles and permissions on views to support read/write permissions for assigned managers to entities.
* Customer jobs & job tracking.
* Client proposals & estimates.
* User preferences and settings & account creation views.
* Update package and code documentation.

### Version 0.9

* Enable Hierarchical Entity structures via MPTT.
* Consolidated financial statements.
* Intercompany transactions.
* Update package and code documentation.

### Version 1.0

* Complete Internationalization of all user-related fields.

*** Roadmap subject to change based on user feedback and backlog priorities.



# Want to contribute?

__This project is actively looking for contributors. Any financial and/or accounting experience is a big plus.__
If you have prior accounting experience and want to contribute, don't hesitate to contact me.
See __[contribution guidelines](https://github.com/arrobalytics/django-ledger/blob/develop/Contribute.md)__.

# Contrib Packages
* GraphQL API - See details [here.](https://github.com/arrobalytics/django-ledger/tree/develop/django_ledger/contrib/django_ledger_graphql)

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

# How To Set Up Django Ledger for Development
Django Ledger comes with a basic development environment already configured under __dev_env/__ folder not to be used
for production environments. If you want to contribute to the project perform the following steps:

1. Navigate to your projects directory.
2. Clone the repo from github and CD into project.
```shell
git clone https://github.com/arrobalytics/django-ledger.git && cd django-ledger
```
3. Install PipEnv, if not already installed:
```shell
pip install -U pipenv
```
4. Create virtual environment.
```shell
pipenv install
```
If using a specific version of Python you may specify the path.
```shell
pipenv install --python PATH_TO_INTERPRETER
```
5. Activate environment.
```shell
pipenv shell
```
6. Apply migrations.
```shell
python manage.py migrate
```
7. Create a Development Django user.
```shell
python manage.py createsuperuser
```
8. Run development server.
```shell
python manage.py runserver
```

# Run Test Suite
After setting up your development environment you may run tests.
```shell
python manage.py test django_ledger
```

# Screenshots
![django ledger entity dashboard](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_entity_dashboard.png)
![django ledger balance sheet](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_income_statement.png)
![django ledger income statement](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_balance_sheet.png)
![django ledger bill](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_bill.png)
![django ledger invoice](https://us-east-1.linodeobjects.com/django-ledger/public/img/django_ledger_invoice.png)
