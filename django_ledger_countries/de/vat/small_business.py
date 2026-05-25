"""
Kleinunternehmer (§ 19 UStG) — no VAT lines; gross amounts stay on revenue/expense accounts.
"""
from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from django_ledger_countries.de.vat.base import VatRegimeHandler
from django_ledger_countries.de.vat.context import VatContext


class SmallBusinessVatHandler(VatRegimeHandler):
    code = 'small_business'

    def adjust_posting(self, ctx: VatContext, document, transactions: list) -> list:
        return transactions

    def validate_journal_entry(self, ctx: VatContext, journal_entry) -> None:
        self._raise_if_vat_accounts_used(
            ctx,
            journal_entry,
            regime_label=str(_('Kleinunternehmer')),
        )

    def invoice_vat_notice(self, ctx: VatContext) -> str:
        return str(
            _(
                'No VAT is shown pursuant to § 19 UStG (Kleinunternehmerregelung). '
                'VAT is not charged.'
            )
        )
