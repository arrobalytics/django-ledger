"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.core.exceptions import ValidationError


class DjangoLedgerConfigurationError(Exception):
    pass


class InvalidDateInputError(ValidationError):
    pass


class InvalidRoleError(ValidationError):
    pass


class TransactionNotInBalanceError(ValidationError):
    pass
