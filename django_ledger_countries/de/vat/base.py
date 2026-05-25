"""
Base class for pluggable German VAT regime handlers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from django.core.exceptions import ValidationError

from django_ledger_countries.de.vat.context import VatContext


class VatRegimeHandler(ABC):
    code: str

    @abstractmethod
    def adjust_posting(self, ctx: VatContext, document, transactions: list) -> list:
        """Return transactions after regime-specific VAT adjustments."""

    def validate_journal_entry(self, ctx: VatContext, journal_entry) -> None:
        """Optional compliance checks before a journal entry is posted."""

    def invoice_vat_notice(self, ctx: VatContext) -> str:
        """Legal footnote for customer invoices (empty when not applicable)."""
        return ''

    def _iter_journal_transactions(self, journal_entry):
        if hasattr(journal_entry, 'transactionmodel_set'):
            return journal_entry.transactionmodel_set.select_related('account').all()
        return getattr(journal_entry, 'txs', [])

    def _raise_if_vat_accounts_used(self, ctx: VatContext, journal_entry, *, regime_label: str) -> None:
        from django_ledger_countries.de.roles import ASSET_CA_VAT_RECEIVABLE, LIABILITY_CL_VAT_PAYABLE

        vat_roles = {ASSET_CA_VAT_RECEIVABLE, LIABILITY_CL_VAT_PAYABLE}
        for tx in self._iter_journal_transactions(journal_entry):
            account = getattr(tx, 'account', None)
            if account is not None and account.role in vat_roles:
                raise ValidationError(
                    f'VAT clearing accounts cannot be used while the entity is on the '
                    f'{regime_label} tax regime.'
                )
