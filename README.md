![django ledger logo](https://us-east-1.linodeobjects.com/django-ledger/logo/django-ledger-logo@2x.png)

### An Accounting, Bookkeeping & Financial Analysis Engine for the Django Framework.

__Django Ledger__ is a double entry accounting system based on
the [Django Web Framework](https://www.djangoproject.com),
which aims to power financially driven applications by removing the complexity of the accounting domain into a simple,
high-level API. _Prior experience with Django is required to more effectively use this software_.

__Django Ledger__ was created and is currently maintained and developed by lead developer Miguel Sanda.
If you want to contribute please consider joining our new discord channel here.

### Join our Discord Channel [Here](https://discord.gg/PEugR227)

The software is still in early stages of development. For more information, please check the
[Roadmap](https://github.com/arrobalytics/django-ledger/blob/develop/ROADMAP.md).

### How long until all features are implemented?

Finance and Accounting is a complicated subject. Django Ledger is different from other Django projects
as it aims to provide a developer-friendly accounting engine while providing a reliable and extensible API to
power financially driven applications. This project in particular, not only requires Python AND Django programming
experience, but also finance and accounting experience. So, that's the long way of saying, we need your help!
Join our Discord Channel [here](https://discord.gg/PEugR227) to learn more.

__This project can greatly benefit from contributions towards Documentation and Unit Tests.__
__This is the best way to get started twith this project if you are not familiar with the models.__

### Documentation

Access the latest documentation and QuickStart guide [here](https://django-ledger.readthedocs.io/en/latest/).
Also, you may download the QuickStart Jupyter Notebook
[here](https://github.com/arrobalytics/django-ledger/blob/develop/notebooks/QuickStart%20Notebook.ipynb).

Django Ledger supports:

- Double entry accounting.
- Hierarchical Chart of Accounts.
- Financial Statements (Income Statement, Balance Sheet & Cash Flow Statement).
- Purchase Orders, Sales Orders (Estimates), Bills and Invoices.
- Automatic financial ratio & insight calculations.
- High Level Entity API.
- Multi tenancy (multiple companies/users/clients).
- Self-contained Ledgers, Journal Entries & Transactions.
- Basic OFX & QFX file import.
- Bills & Invoices with optional cash/accrual functionality.
- Basic navigational templates.
- Entity administration & entity manager support.
- Items, lists & inventory management.
- Unit of Measures.
- Bank Accounts.

# Roadmap to Version 1.0.

### ~~Version 0.4~~ *completed*

* __0.4.0__: Items, resources and & lists for bills & invoices itemization:
* __0.4.0__: Enhance and optimize Django Ledger the random data generation functionality to properly populate relevant
  random data for testing.
* __0.4.1__: Entity internal organizations, department, branches, etc.
* __0.4.2__: Custom Accounting Periods.
* __0.4.3__: Purchase Order Model implementation.
* Bugfixes & UI/UX Enhancements.

### Version 0.5

More details available in the [Django Ledger v0.5 Page](https://www.arrobalytics.com/blog/2021/12/07/django-ledger-v05/)
.

* __0.5__: Testing framework implementation that will include:
    * Unit tests using the [Built-in Django](https://docs.djangoproject.com/en/3.1/topics/testing/) unit test modules.
    * Behavioral Driven Testing using [behave](https://behave.readthedocs.io/en/latest/) library.
    * __Need help!!!! If you want to contribute PLEASE ADD UNIT TESTS!!!__
    * Start creating basic package documentation via [Sphinx](https://www.sphinx-doc.org/en/master/)
        * Document code and functions within code base.
        * Generate HTML documentation.
    * Work with Accountants, Subject Experts and Developers to define an initial list of Unit Tests to validate output _
      _(
      help needed!)__.
    * Update package and code documentation.
    * Bugfixes & UI/UX Enhancements.
* ~~__0.5.0__~~: Inventory tracking.
    * Average Cost.
* ~~__0.5.1__~~: Customer estimates & contract tracking.
    * Link Estimate/PO/Bill/Invoice workflow.
    * Journal Entry activity determination & validation (for cash flow).
* ~~__0.5.2__~~: Cash flow statement.
    * Human Readable Journal Entry document numbers.
    * Hierarchical Account Model Management.
    * Generate all Django Ledger Model documentation.
* ~~__0.5.3__~~: High Level EntityModel API.
* ~~__0.5.4__~~: Balance Sheet Statement, Income Statement & Cash Flow Statement API & PDF report export.
* __0.5.5__: Closing Entries.
  * 0.5.5.1: Closing Entries will be used if requested date is present. Documentation Update.
* __0.5.6__: Chart of Accounts Import.
* __0.5.7__: Trial Balance Import.
* __0.5.8__: GraphQL API.

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
* User preferences and settings & account creation views.
* Update package and code documentation.

### Version 0.9

* Enable Hierarchical Entity Structures.
* Consolidated financial statements.
* InterCompany transactions.
* Update package and code documentation.

### Version 1.0

* Complete Internationalization of all user-related fields.

*** Roadmap subject to change based on user feedback and backlog priorities.

# Want to contribute?

__This project is actively looking for contributors. Any financial and/or accounting experience is a big plus.__
If you have prior accounting experience and want to contribute, don't hesitate to contact me.
See __[contribution guidelines](https://github.com/arrobalytics/django-ledger/blob/develop/Contribute.md)__.

# Contrib Packages

* GraphQL API - See
  details [here.](https://github.com/arrobalytics/django-ledger/tree/develop/django_ledger/contrib/django_ledger_graphql)

# Installation

Django Ledger is a [Django](https://www.djangoproject.com/) application. If you haven't, you need a working knowledge of
Django and a working Django
Project before you can use Django Ledger. A good place to start
is [here](https://docs.djangoproject.com/en/4.2/intro/tutorial01/#creating-a-project).
Make sure you refer to the django version you are using. A quick way to start a new django project is to run the
following command:

* Install Django:

```shell
pip install django
```

* Install Python Pipenv:

```shell script
pip install pipenv
```

* Go to your desired development folder and create a new django project:

```shell
django-admin startproject django_ledger_project && cd django_ledger_project
```

* Install Django on you virtual environment.

```shell
pipenv install django
```

* Install Django Ledger

```shell script
pipenv install django-ledger[graphql,pdf]
```

* Activate your new virtual environment:

```shell
pipenv shell
```

* Add django_ledger to INSTALLED_APPS in you new Django Project.

```python
INSTALLED_APPS = [
    ...,
    'django_ledger',
    ...,
]
```

* Perform database migrations:

```shell
python manage.py migrate
```

* Add Django SuperUser and follow the prompts.

```shell
python manage.py createsuperuser
```

* Add URLs to your project's __urls.py__:

```python
from django.urls import include, path

urlpatterns = [
    ...,
    path('ledger/', include('django_ledger.urls', namespace='django_ledger')),
    ...,
]
```

* Run your project:

```shell
python manage.py runserver
```

* Navigate to Django Ledger root view assigned in your project urlpatterns setting (typically http://127.0.0.1:8000/ledger
if you followed this installation guide).
* Use your superuser credentials to login.

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

# Financial Statements Screenshots

![balance_sheet_report](https://django-ledger.us-east-1.linodeobjects.com/public/img/BalanceSheetStatement.png)
![income_statement_report](https://django-ledger.us-east-1.linodeobjects.com/public/img/IncomeStatement.png)
![cash_flow_statement_report](https://django-ledger.us-east-1.linodeobjects.com/public/img/CashFlowStatement.png)
