"""
DATEV-compatible account code validation for Germany (SKR03).
"""
from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# DATEV SKR03 export format: "1200 00" (4 digits, space, 2-digit suffix)
DATEV_ACCOUNT_CODE_RE = re.compile(r'^\d{4} \d{2}$')


def validate_datev_account_code(code: str) -> None:
    if not code:
        raise ValidationError(_('Account code is required.'))
    if not DATEV_ACCOUNT_CODE_RE.match(code):
        raise ValidationError(
            _('Account code must match DATEV SKR03 format "NNNN NN", got {%(code)s}.'),
            params={'code': code},
        )


def parse_datev_account_code(account_number: str) -> tuple[int, int]:
    """
    Parse a DATEV account number into main (4-digit) and suffix (2-digit) parts.
    """
    validate_datev_account_code(account_number)
    main_str, suffix_str = account_number.split(' ')
    return int(main_str), int(suffix_str)
