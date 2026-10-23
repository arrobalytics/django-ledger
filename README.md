![django ledger logo](assets/logo/django-ledger-logo@2x.png)

# Django Ledger

### A Double Entry Accounting Engine for Django

Django Ledger is a powerful, high-performance financial management and double-entry accounting engine built on top of the Django Web Framework. It provides a robust, developer-friendly API and modular architecture for handling complex accounting tasks in financially driven applications.

Created and developed by [Miguel Sanda](https://www.miguelsanda.com).

[FREE Get Started Guide](https://www.djangoledger.com/get-started) | [Join our Discord](https://discord.gg/c7PZcbYgrc) | [Documentation](https://django-ledger.readthedocs.io/en/latest/) | [QuickStart Notebook](https://github.com/arrobalytics/django-ledger/blob/develop/notebooks/QuickStart%20Notebook.ipynb)

---

## 🚀 Key Features

- **Double-Entry Accounting Engine**: Strict balancing and transactional integrity.
- **Hierarchical Chart of Accounts**: Flexible, multi-level account organization.
- **Financial Statements**: Automated Income Statement, Balance Sheet, and Cash Flow Statement generation.
- **Commercial Documents**: Purchase Orders, Sales Orders, Bills, and Invoices.
- **Financial Ratios & Analytics**: Built-in calculation of key financial metrics.
- **Multi-Tenancy Support**: Robust entity and organizational isolation.
- **Ledgers, Journal Entries & Transactions**: Comprehensive general ledger management.
- **Banking & Imports**: OFX & QFX file import capabilities.
- **Closing Entries & Inventory**: Fiscal year-end closing and inventory management with Units of Measure.
- **Django Admin Integration**: Seamless management and built-in Entity Management UI.

---

## 📦 Installation & Quick Start

Django Ledger is a [Django](https://www.djangoproject.com/) application. You should have a working Django project before integrating Django Ledger.

### 1. Add to `INSTALLED_APPS`

Add `'django_ledger'` to your project's `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    ...,
    'django_ledger',
    ...,
]
```

### 2. Configure Context Preprocessor

Add the Django Ledger context preprocessor to your templates configuration:

```python
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                '...',
                'django_ledger.context.django_ledger_context',
            ],
        },
    },
]
```

### 3. Configure URL Routing

Include Django Ledger URLs in your project's root `urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    ...,
    path('ledger/', include('django_ledger.urls', namespace='django_ledger')),
    ...,
]
```

### 4. Run Database Migrations

Apply database migrations:

```shell
python manage.py migrate
```

### 5. Run Your Project

```shell
python manage.py runserver
```

Navigate to `http://127.0.0.1:8000/ledger` and log in using your superuser credentials.

---

## ⚙️ Deprecated Behavior Setting (v0.8.0+)

Starting with version `v0.8.0`, Django Ledger introduces the `DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR` setting to control 
access to deprecated features and legacy behaviors.

- **Default**: `False` (deprecated features are disabled by default).
- To temporarily continue using deprecated features during your migration, set `DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR = True` in your Django settings.

---

## 🛠️ Setting Up Django Ledger for Development (Using `uv`)

Django Ledger uses [Astral uv](https://github.com/astral-sh/uv) for lightning-fast dependency management and virtual environment handling.

### Prerequisites

Make sure you have Python (>= 3.11) and `uv` installed. If you don't have `uv` installed:

```shell
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv
```

### Development Setup Steps

1. **Clone the repository and navigate into the project directory:**

   ```shell
   git clone https://github.com/arrobalytics/django-ledger.git
   cd django-ledger
   ```

2. **Create the virtual environment and sync dependencies:**

   `uv` will automatically create a virtual environment and install all dependencies (including development tools) specified in `pyproject.toml` and locked in `uv.lock`:

   ```shell
   uv sync
   ```

3. **Activate the virtual environment (optional, or use `uv run`):**

   ```shell
   source .venv/bin/activate
   ```

4. **Apply database migrations:**

   ```shell
   uv run python manage.py migrate
   ```
   *(Or simply `python manage.py migrate` if your virtual environment is activated)*

5. **Create a superuser account:**

   ```shell
   uv run python manage.py createsuperuser
   ```

6. **Run the development server:**

   ```shell
   uv run python manage.py runserver
   ```

### Database Dependency Groups

If you prefer using a database backend other than the default SQLite (such as PostgreSQL, MySQL, or MariaDB), `uv` provides dependency groups that you can sync:

- **PostgreSQL**:
  ```shell
  uv sync --group postgresql
  ```
  Installs `psycopg[pool,binary]`.

- **MySQL**:
  ```shell
  uv sync --group mysql
  ```
  Installs `mysqlclient`.
- **MariaDB**:
  ```shell
  uv sync --group mariadb
  ```
  Installs `mariadb`.
You can also combine multiple dependency groups when syncing (e.g., `uv sync --group dev --group postgresql`).
---
## 🐳 Setting Up Development Using Docker
If you prefer containerized development:
Clone the repository and navigate into it.
1. Ensure `'0.0.0.0'` is included in `ALLOWED_HOSTS` in your Django settings.
2. Build and start the containers using Docker Compose:
   ```shell
   docker compose up --build
   ```
3. In a separate terminal, create a superuser inside the container:
   ```shell
   docker ps
   # Find your container ID or name
   docker exec -it <container_id> python manage.py createsuperuser
   ```
4. Open `http://127.0.0.1:8000/ledger` in your browser.
---
## 🤝 Getting Involved & Contributing
Contributions are welcome. Please read [Contribute.md](Contribute.md) before opening a pull request.
A signed Contributor License Agreement is required for all contributions, including code, tests, documentation, and 
other project materials. Pull requests should target the `dev` branch.
- **Feature Requests & Bug Reports**: Open an issue on GitHub.
- **Questions and implementation help**: Contact [Miguel Sanda](https://www.miguelsanda.com/work-with-me/) or email `msanda@arrobalytics.com`.
- **Contribution Guidelines**: See [Contribute.md](Contribute.md).
### Who Should Contribute?

- Python and Django developers.
- Finance, accounting, and bookkeeping experts.
- Anyone passionate about building robust financial engines.

---

## 📸 Screenshots

### Entity Dashboard & Core Views
![django ledger entity dashboard](assets/public/img/django_ledger_entity_dashboard.png)
![django ledger balance sheet](assets/public/img/django_ledger_income_statement.png)
![django ledger income statement](assets/public/img/django_ledger_balance_sheet.png)
![django ledger bill](assets/public/img/django_ledger_bill.png)
![django ledger invoice](assets/public/img/django_ledger_invoice.png)

### Financial Statements
![balance_sheet_report](assets/public/img/BalanceSheetStatement.png)
![income_statement_report](assets/public/img/IncomeStatement.png)
![cash_flow_statement_report](assets/public/img/CashFlowStatement.png)
