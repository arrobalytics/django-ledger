"""
Resolve the active regional plugin for the running process.
"""
from __future__ import annotations

from functools import lru_cache

from django_ledger.regional.base import RegionalPlugin
from django_ledger.regional.us_fallback import USRegionalPlugin


@lru_cache(maxsize=1)
def get_country_plugin() -> RegionalPlugin:
    """
    Return the active :class:`RegionalPlugin`.

    Delegates to ``django_ledger_countries`` when installed; otherwise returns
    the built-in US passthrough plugin.
    """
    try:
        from django_ledger_countries.registry import get_active_plugin

        return get_active_plugin()
    except ImportError:
        return USRegionalPlugin()


def clear_country_plugin_cache() -> None:
    """Clear the plugin cache (useful in tests)."""
    get_country_plugin.cache_clear()
    try:
        from django_ledger_countries.registry import clear_active_plugin_cache

        clear_active_plugin_cache()
    except ImportError:
        pass
