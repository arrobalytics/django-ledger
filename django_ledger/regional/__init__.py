"""
Regional plugin infrastructure for django-ledger.

Country-specific behavior lives in ``django_ledger_countries``; this package
defines the plugin contract and dispatch helpers used by core.
"""

from django_ledger.regional.base import RegionalPlugin
from django_ledger.regional.registry import get_country_plugin

__all__ = [
    'RegionalPlugin',
    'get_country_plugin',
]
