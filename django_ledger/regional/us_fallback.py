"""
Built-in US regional plugin used when ``django_ledger_countries`` is not installed.

Preserves upstream django-ledger default behavior.
"""
from __future__ import annotations

from typing import Any, Dict

from django_ledger.regional.base import RegionalPlugin


class USRegionalPlugin(RegionalPlugin):
    code = 'us'

    def get_setting_defaults(self) -> Dict[str, Any]:
        return {
            'CURRENCY_SYMBOL': '$',
            'SPACED_CURRENCY_SYMBOL': False,
            'REQUIRE_SUPPORTING_DOCUMENT_ON_POST': False,
            'DEFAULT_COA': None,
        }

    def validate_account_code(self, code: str) -> None:
        from django.core.exceptions import ValidationError
        from django.utils.translation import gettext_lazy as _

        if not code or not code.isalnum():
            raise ValidationError(_('Account code must be alpha numeric, got {%s}') % code)

    def enforce_account_code_prefix(self) -> bool:
        return True
