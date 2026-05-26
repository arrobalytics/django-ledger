"""
Settings for django_ledger_extensions (global Django settings overrides).
"""
from __future__ import annotations

from functools import lru_cache

from django.conf import settings as django_settings

SETTING_NAMES = (
    'REMINDER_DEFAULT_LEAD_DAYS',
    'REMINDER_GRACE_DAYS',
    'REMINDER_FROM_EMAIL',
    'HEALTH_CHECK_STALE_DRAFT_DAYS',
    'BANK_MATCH_AMOUNT_TOLERANCE',
    'BANK_MATCH_DAY_TOLERANCE',
)

DEFAULTS = {
    'REMINDER_DEFAULT_LEAD_DAYS': 14,
    'REMINDER_GRACE_DAYS': 3,
    'REMINDER_FROM_EMAIL': None,
    'HEALTH_CHECK_STALE_DRAFT_DAYS': 14,
    'BANK_MATCH_AMOUNT_TOLERANCE': '0.01',
    'BANK_MATCH_DAY_TOLERANCE': 7,
}


def get_extension_setting(name: str):
    if name not in SETTING_NAMES:
        raise KeyError(f'Unknown extension setting: {name}')
    global_key = f'DJANGO_LEDGER_{name}'
    if hasattr(django_settings, global_key):
        return getattr(django_settings, global_key)
    return DEFAULTS[name]


@lru_cache(maxsize=1)
def get_reminder_from_email() -> str:
    configured = get_extension_setting('REMINDER_FROM_EMAIL')
    if configured:
        return configured
    return getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost')
