Requirements
------------

* Python 3.4+
* Django 2.0+

Installation
------------

Install with pip::

    pip install django-ledger

Add `django-ledger` to your `INSTALLED_APPS`

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django-ledger',
        ...
    )

Quickstart
----------

.. code-block:: python

    default_coa = ChartOfAccountsModel.objects.get(slug='default-coa')

    my_entity = EntityModel.objects.create(slug='my-entity',
                                           name='My Entity, Inc.',
                                           coa=default_coa)
