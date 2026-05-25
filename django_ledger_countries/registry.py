"""
Country plugin resolution for ``django_ledger_countries``.
"""
from __future__ import annotations

from functools import lru_cache

from django_ledger.regional.base import RegionalPlugin

from django_ledger_countries.settings import get_country_code, _get_plugin_for_country


@lru_cache(maxsize=1)
def get_active_plugin() -> RegionalPlugin:
    return _get_plugin_for_country(get_country_code())


def clear_active_plugin_cache() -> None:
    from django_ledger_countries.settings import clear_settings_cache

    get_active_plugin.cache_clear()
    clear_settings_cache()
