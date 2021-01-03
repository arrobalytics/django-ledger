Installation
=============

Django Ledger has only one dependency to implement the tree-like structure of Entities,
Accounts and Journal Entries. Django MPTT does not provide any models, but provides a
versatile Model Admin that implements hierarchy between objects.

>>> pip install django-mptt

Or if using Pipenv:

>>> pipenv install

Add **mptt** and **django_ledger** to your installed apps.

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'django_ledger',
        ...
    ]

Include Djetler's URLs in your project.

.. code-block:: python

    urlpatterns = [
        ...
        path('', include('django_ledger.urls', namespace='django_ledger')),
        ...
    ]

Now run Django Ledger's migrations.

    >>> python manage.py migrate django_ledger