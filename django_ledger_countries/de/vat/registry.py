"""
Registry of VAT regime handlers.
"""
from __future__ import annotations

from typing import Dict

from django_ledger_extensions.models import EntityTaxProfile

from django_ledger_countries.de.vat.base import VatRegimeHandler
from django_ledger_countries.de.vat.exempt import ExemptVatHandler
from django_ledger_countries.de.vat.small_business import SmallBusinessVatHandler
from django_ledger_countries.de.vat.standard import StandardVatHandler

_HANDLERS: Dict[str, VatRegimeHandler] = {
    EntityTaxProfile.TaxRegime.STANDARD: StandardVatHandler(),
    EntityTaxProfile.TaxRegime.SMALL_BUSINESS: SmallBusinessVatHandler(),
    EntityTaxProfile.TaxRegime.EXEMPT: ExemptVatHandler(),
}


def get_vat_handler(regime: str) -> VatRegimeHandler:
    try:
        return _HANDLERS[regime]
    except KeyError as exc:
        raise KeyError(f'Unknown VAT regime: {regime}') from exc
