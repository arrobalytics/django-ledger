"""
SKR03 account codes and starter-set filtering per VAT regime.
"""
from __future__ import annotations

from typing import FrozenSet, Iterable, Set

from django_ledger_extensions.models import EntityTaxProfile

VAT_INPUT_CODE = '1576 00'
VAT_OUTPUT_CODE = '1776 00'
TAXABLE_REVENUE_CODE = '8400 00'
EXEMPT_REVENUE_CODE = '8100 00'

VAT_ACCOUNT_CODES: FrozenSet[str] = frozenset({VAT_INPUT_CODE, VAT_OUTPUT_CODE})
TAXABLE_REVENUE_CODES: FrozenSet[str] = frozenset({TAXABLE_REVENUE_CODE})
EXEMPT_REVENUE_CODES: FrozenSet[str] = frozenset({EXEMPT_REVENUE_CODE})


def filter_starter_codes_for_regime(
    codes: Iterable[str],
    regime: str,
) -> Set[str]:
    """
    Return the subset of *codes* that should be active for *regime*.

    - ``standard`` — taxable revenue + VAT clearing accounts
    - ``exempt`` — § 4 UStG style exempt revenue; no VAT accounts
    - ``small_business`` — Kleinunternehmer § 19; gross revenue, no VAT accounts
    """
    filtered = set(codes)
    if regime == EntityTaxProfile.TaxRegime.STANDARD:
        filtered -= EXEMPT_REVENUE_CODES
        return filtered
    if regime == EntityTaxProfile.TaxRegime.EXEMPT:
        filtered -= VAT_ACCOUNT_CODES | TAXABLE_REVENUE_CODES
        return filtered
    if regime == EntityTaxProfile.TaxRegime.SMALL_BUSINESS:
        filtered -= VAT_ACCOUNT_CODES | TAXABLE_REVENUE_CODES | EXEMPT_REVENUE_CODES
        return filtered
    return filtered
