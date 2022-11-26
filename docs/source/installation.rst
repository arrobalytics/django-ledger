Installation
=============

The easiest way to install the latest Django Ledger version is to install it directly
from the repository.

>>> pip install django-ledger

Add **django_ledger** to your installed apps.

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'django_ledger',
        ...
    ]

Include Django Ledger's URLs in your project.

.. code-block:: python

    from django.urls import path, include

.. code-block:: python

    urlpatterns = [
        ...
        path('ledger/', include('django_ledger.urls', namespace='django_ledger')),
        ...
    ]

Now run Django Ledger's migrations.

    >>> python manage.py migrate django-ledger