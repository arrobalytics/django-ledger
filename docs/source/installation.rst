Installation
====================

Django Ledger has only one dependency to implement the tree-like structure of Entities,
Accounts and Journal Entries. Django MPTT does not provide any models, but provides a
versatile Model Admin that implements hierarchy between objects.

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'mptt', # Djetler dependency ...
        'django_ledger',
        ...
    ]

Now let's run Djetler's migrations.

    >>> python manage.py migrate django_ledger