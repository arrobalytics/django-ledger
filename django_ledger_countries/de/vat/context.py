"""
Shared context for German VAT regime handlers.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django_ledger_extensions.models import EntityTaxProfile


@dataclass(frozen=True)
class VatContext:
    entity: object
    tax_profile: EntityTaxProfile
    vat_rate: Decimal
    coa: object

    @classmethod
    def from_document(cls, document) -> Optional[VatContext]:
        ledger = getattr(document, 'ledger', None)
        if ledger is None:
            return None
        entity = getattr(ledger, 'entity', None)
        if entity is None:
            return None
        try:
            tax_profile = entity.tax_profile
        except Exception:
            return None
        coa = entity.default_coa
        if coa is None:
            return None
        vat_rate = Decimal(str(tax_profile.default_vat_rate or 0))
        return cls(entity=entity, tax_profile=tax_profile, vat_rate=vat_rate, coa=coa)
