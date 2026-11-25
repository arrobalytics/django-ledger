"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Support for the optional demo extra.

Sample data comes from EntityDataGenerator, which needs Faker. Faker is not a core dependency of Django Ledger. It is
installed with the demo extra: pip install "django-ledger[demo]". This module tells the rest of the package whether
Faker is available, without importing it, and holds the message shown to users when it is missing.
"""

from importlib.util import find_spec

from django.utils.translation import gettext_lazy as _

DEMO_EXTRA_INSTALL_COMMAND: str = 'pip install "django-ledger[demo]"'

FAKER_INSTALLED: bool = find_spec('faker') is not None

FAKER_MISSING_MESSAGE = _(
    'Sample data needs the Faker library, which is not installed. Install it with: pip install "django-ledger[demo]"'
)
