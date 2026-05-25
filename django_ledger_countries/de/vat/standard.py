"""
Standard German VAT (Regelbesteuerung) — split gross amounts into net + VAT.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from django_ledger.io.roles import GROUP_COGS, GROUP_EXPENSES, GROUP_INCOME
from django_ledger.models.utils import lazy_loader

from django_ledger_countries.de.roles import ASSET_CA_VAT_RECEIVABLE, LIABILITY_CL_VAT_PAYABLE
from django_ledger_countries.de.vat.base import VatRegimeHandler
from django_ledger_countries.de.vat.context import VatContext

VATABLE_CREDIT_ROLES = set(GROUP_INCOME)
VATABLE_DEBIT_ROLES = set(GROUP_COGS + GROUP_EXPENSES)


class StandardVatHandler(VatRegimeHandler):
    code = 'standard'

    def adjust_posting(self, ctx: VatContext, document, transactions: list) -> list:
        if ctx.vat_rate <= 0:
            return transactions

        TransactionModel = lazy_loader.get_txs_model()
        vat_input = ctx.coa.accountmodel_set.filter(
            role=ASSET_CA_VAT_RECEIVABLE, active=True
        ).first()
        vat_output = ctx.coa.accountmodel_set.filter(
            role=LIABILITY_CL_VAT_PAYABLE, active=True
        ).first()
        if not vat_input and not vat_output:
            return transactions

        account_roles = self._account_roles(transactions)
        description = getattr(document, 'get_migrate_state_desc', lambda: 'VAT adjustment')()
        extra: List = []

        for tx in transactions:
            role = account_roles.get(tx.account_id)
            if role is None:
                continue
            if tx.tx_type == 'credit' and role not in VATABLE_CREDIT_ROLES:
                continue
            if tx.tx_type == 'debit' and role not in VATABLE_DEBIT_ROLES:
                continue

            gross = Decimal(str(tx.amount))
            net = (gross / (Decimal('1') + ctx.vat_rate)).quantize(Decimal('0.01'))
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

    @staticmethod
    def _account_roles(transactions: list) -> Dict[object, str]:
        roles_by_id: Dict[object, str] = {}
        for tx in transactions:
            account = getattr(tx, 'account', None)
            if account is not None and getattr(account, 'role', None):
                roles_by_id[tx.account_id] = account.role
        missing_ids = {tx.account_id for tx in transactions if tx.account_id not in roles_by_id}
        if missing_ids:
            AccountModel = lazy_loader.get_account_model()
            for account in AccountModel.objects.filter(uuid__in=missing_ids):
                roles_by_id[account.uuid] = account.role
        return roles_by_id
