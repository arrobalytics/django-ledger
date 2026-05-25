"""
Pluggable German VAT posting by entity tax regime.

Toggle per entity via ``EntityTaxProfile.tax_regime`` (Django admin). New entities
default from ``DJANGO_LEDGER_DE_DEFAULT_TAX_REGIME`` / ``DEFAULT_VAT_RATE`` settings.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django_ledger_extensions.models import EntityTaxProfile

from django_ledger_countries.de.vat.accounts import filter_starter_codes_for_regime
from django_ledger_countries.de.vat.context import VatContext
from django_ledger_countries.de.vat.registry import get_vat_handler
from django_ledger_countries.de.vat.reporting import (
    build_vat_quarterly_report,
    format_vat_quarterly_report,
)
from django_ledger_countries.settings import get_ledger_setting


def get_default_tax_profile_values() -> dict:
    regime = get_ledger_setting('DEFAULT_TAX_REGIME')
    valid = {choice.value for choice in EntityTaxProfile.TaxRegime}
    if regime not in valid:
        regime = EntityTaxProfile.TaxRegime.EXEMPT

    if regime == EntityTaxProfile.TaxRegime.STANDARD:
        rate = get_ledger_setting('DEFAULT_VAT_RATE')
        return {
            'tax_regime': regime,
            'default_vat_rate': rate if rate is not None else '0.19',
        }
    return {
        'tax_regime': regime,
        'default_vat_rate': '0',
    }


def get_vat_handler_for_profile(tax_profile: EntityTaxProfile):
    return get_vat_handler(tax_profile.tax_regime)


def adjust_posting(document, transactions: list) -> list:
    ctx = VatContext.from_document(document)
    if ctx is None:
        return transactions
    handler = get_vat_handler(ctx.tax_profile.tax_regime)
    return handler.adjust_posting(ctx, document, transactions)


def validate_vat_journal_entry(journal_entry) -> None:
    ledger = getattr(journal_entry, 'ledger', None)
    entity = getattr(ledger, 'entity', None) if ledger else None
    if entity is None:
        return
    try:
        tax_profile = entity.tax_profile
    except Exception:
        return
    ctx = VatContext(
        entity=entity,
        tax_profile=tax_profile,
        vat_rate=Decimal(str(tax_profile.default_vat_rate or 0)),
        coa=entity.default_coa,
    )
    handler = get_vat_handler(tax_profile.tax_regime)
    handler.validate_journal_entry(ctx, journal_entry)


def invoice_vat_notice_for_entity(entity) -> str:
    try:
        tax_profile = entity.tax_profile
    except Exception:
        return ''
    if entity.default_coa is None:
        return ''
    ctx = VatContext(
        entity=entity,
        tax_profile=tax_profile,
        vat_rate=Decimal(str(tax_profile.default_vat_rate or 0)),
        coa=entity.default_coa,
    )
    return get_vat_handler(tax_profile.tax_regime).invoice_vat_notice(ctx)


def apply_regime_starter_activation(coa_model, tax_regime: Optional[str] = None) -> int:
    """Activate starter accounts appropriate for *tax_regime* (defaults to entity profile)."""
    from django_ledger_countries.de.coa.starter import apply_starter_activation, get_starter_account_codes

    if tax_regime is None:
        entity = coa_model.entity
        try:
            tax_regime = entity.tax_profile.tax_regime
        except Exception:
            tax_regime = get_default_tax_profile_values()['tax_regime']

    starter_codes = filter_starter_codes_for_regime(get_starter_account_codes(), tax_regime)
    return apply_starter_activation(coa_model, starter_codes=starter_codes)
