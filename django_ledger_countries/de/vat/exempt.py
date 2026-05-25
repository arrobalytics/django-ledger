"""
Tax-exempt education provider (§ 4 UStG) — no VAT lines on exempt supplies.
"""
from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from django_ledger_countries.de.vat.base import VatRegimeHandler
from django_ledger_countries.de.vat.context import VatContext


class ExemptVatHandler(VatRegimeHandler):
    code = 'exempt'

    def adjust_posting(self, ctx: VatContext, document, transactions: list) -> list:
        return transactions

    def validate_journal_entry(self, ctx: VatContext, journal_entry) -> None:
        self._raise_if_vat_accounts_used(
            ctx,
            journal_entry,
            regime_label=str(_('tax-exempt school')),
        )

    def invoice_vat_notice(self, ctx: VatContext) -> str:
        return str(
            _(
                'This service is exempt from VAT pursuant to § 4 UStG '
                '(tax-exempt education/training).'
            )
        )
