"""
Layered settings resolution for django-ledger country plugins.

Resolution order (highest priority first):

1. ``DJANGO_LEDGER_{COUNTRY}_{NAME}``  e.g. ``DJANGO_LEDGER_DE_DEFAULT_COA``
2. ``DJANGO_LEDGER_{NAME}``            global override
3. Active country plugin defaults
4. Built-in US defaults / core django-ledger settings
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

from django.conf import settings as django_settings

SETTING_NAMES = (
    'CURRENCY_SYMBOL',
    'SPACED_CURRENCY_SYMBOL',
    'REQUIRE_SUPPORTING_DOCUMENT_ON_POST',
    'DEFAULT_COA',
)

CORE_SETTING_MAP = {
    'CURRENCY_SYMBOL': 'DJANGO_LEDGER_CURRENCY_SYMBOL',
    'SPACED_CURRENCY_SYMBOL': 'DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL',
}


@lru_cache(maxsize=1)
def get_country_code() -> str:
    return getattr(django_settings, 'DJANGO_LEDGER_COUNTRY', 'us').lower()


def get_ledger_setting(name: str, default: Any = None) -> Any:
    if name not in SETTING_NAMES:
        raise KeyError(f'Unknown ledger setting: {name}')

    country = get_country_code()
    country_key = f'DJANGO_LEDGER_{country.upper()}_{name}'
    global_key = f'DJANGO_LEDGER_{name}'

    if hasattr(django_settings, country_key):
        return getattr(django_settings, country_key)

    if hasattr(django_settings, global_key):
        return getattr(django_settings, global_key)

    plugin = _get_plugin_for_country(country)
    plugin_default = plugin.get_setting_defaults().get(name)
    if plugin_default is not None:
        return plugin_default

    core_key = CORE_SETTING_MAP.get(name)
    if core_key:
        return getattr(django_settings, core_key, default)

    return default


def _get_plugin_for_country(country: str):
    from django_ledger_countries.us.plugin import USRegionalPlugin

    return USRegionalPlugin()


def clear_settings_cache() -> None:
    get_country_code.cache_clear()
