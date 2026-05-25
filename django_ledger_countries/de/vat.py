"""
German VAT posting adjustments.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List

from django_ledger.models.utils import lazy_loader

from django_ledger_countries.de.roles import ASSET_CA_VAT_RECEIVABLE, LIABILITY_CL_VAT_PAYABLE


def _get_entity(document):
    ledger = getattr(document, 'ledger', None)
    if ledger is None:
        return None
    return getattr(ledger, 'entity', None)


def _get_tax_profile(entity):
    if entity is None:
        return None
    try:
        return entity.tax_profile
    except Exception:
        return None


def adjust_posting(document, transactions: list) -> list:
    """
    Append VAT split transactions for standard German entities.

    Kleinunternehmer and exempt entities pass through unchanged (no VAT lines).
    """
    entity = _get_entity(document)
    tax_profile = _get_tax_profile(entity)
    if tax_profile is None:
        return transactions

    if tax_profile.tax_regime != tax_profile.TaxRegime.STANDARD:
        return transactions

    vat_rate = Decimal(str(tax_profile.default_vat_rate or 0))
    if vat_rate <= 0:
        return transactions

    TransactionModel = lazy_loader.get_txs_model()
    coa = entity.default_coa
    if coa is None:
        return transactions

    vat_input = coa.accountmodel_set.filter(role=ASSET_CA_VAT_RECEIVABLE, active=True).first()
    vat_output = coa.accountmodel_set.filter(role=LIABILITY_CL_VAT_PAYABLE, active=True).first()
    if not vat_input and not vat_output:
        return transactions

    extra = []
    description = getattr(document, 'get_migrate_state_desc', lambda: 'VAT adjustment')()

    for tx in transactions:
        gross = Decimal(str(tx.amount))
        net = (gross / (Decimal('1') + vat_rate)).quantize(Decimal('0.01'))
        vat_amount = gross - net
        if vat_amount <= 0:
            continue

        tx.amount = net

        vat_account = None
        if tx.tx_type == 'debit' and vat_input:
            vat_account = vat_input
        elif tx.tx_type == 'credit' and vat_output:
            vat_account = vat_output

        if vat_account:
            extra.append(
                TransactionModel(
                    journal_entry=tx.journal_entry,
                    amount=vat_amount,
                    tx_type=tx.tx_type,
                    account=vat_account,
                    description=description,
                )
            )

    return transactions + extra
