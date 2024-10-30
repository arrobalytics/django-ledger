![django ledger logo](https://us-east-1.linodeobjects.com/django-ledger/logo/django-ledger-logo@2x.png)

# Django Ledger

## A Double Entry Accounting Engine for Django

Django Ledger is a powerful financial management system built on the Django Web Framework. It offers a simplified API for handling complex accounting tasks in financially driven applications.

[Join our Discord](https://discord.gg/c7PZcbYgrc) | [Documentation](https://django-ledger.readthedocs.io/en/latest/) | [QuickStart Notebook](https://github.com/arrobalytics/django-ledger/blob/develop/notebooks/QuickStart%20Notebook.ipynb)

## Key Features

- High-level API
- Double entry accounting
- Hierarchical Chart of Accounts
- Financial statements (Income Statement, Balance Sheet, Cash Flow)
- Purchase Orders, Sales Orders, Bills, and Invoices
- Financial ratio calculations
- Multi-tenancy support
- Ledgers, Journal Entries & Transactions
- OFX & QFX file import
- Closing Entries
- Inventory management
- Unit of Measures
- Bank account information
- Django Admin integration
- Built-in Entity Management UI

## Getting Involved

- **Feature Requests/Bug Reports**: Open an issue in the repository
- **For software customization, advanced features and consulting services**: 
[Contact us](https://www.miguelsanda.com/work-with-me/) or email msanda@arrobalytics.com
- **Contribute**: See our [contribution guidelines](https://github.com/arrobalytics/django-ledger/blob/master/Contribute.md)

## Who Should Contribute?

We're looking for contributors with:
- Python and Django programming skills
- Finance and accounting expertise
- Interest in developing a robust accounting engine API

If you have relevant experience, especially in accounting, we welcome your pull requests or direct contact.

# Installation

Django Ledger is a [Django](https://www.djangoproject.com/) application. If you haven't, you need working knowledge of
Django and a working Django project before you can use Django Ledger. A good place to start
is [here](https://docs.djangoproject.com/en/4.2/intro/tutorial01/#creating-a-project).

Make sure you refer to the django version you are using.

The easiest way to start is to use the zero-config Django Ledger starter template. See
details [here](https://github.com/arrobalytics/django-ledger-starter). Otherwise, you may create your
project from scratch.

To create a new Django Ledger project:

* Make sure you have the latest version of python [here](https://www.python.org/) (recommended).

* Install Django:

```shell
pip install django
```

* Install Python [Pipenv](https://pipenv.pypa.io/en/latest/) (python package manager):

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

* Navigate to Django Ledger root view assigned in your project urlpatterns setting (
  typically http://127.0.0.1:8000/ledger
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

# How To Set Up Django Ledger for Development using Docker

1. Navigate to your projects directory.

2. Give executable permissions to entrypoint.sh

```shell
sudo chmod +x entrypoint.sh
```

3. Add host '0.0.0.0' into ALLOWED_HOSTS in settings.py.

4. Build the image and run the container.

```shell
docker compose up --build
```

5. Add Django Superuser by running command in seprate terminal

```shell
docker ps
```

Select container id of running container and execute following command

```shell
docker exec -it containerId /bin/sh
```

```shell
python manage.py createsuperuser
```

6. Navigate to http://0.0.0.0:8000/ on browser.

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
