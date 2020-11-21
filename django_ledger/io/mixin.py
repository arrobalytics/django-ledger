"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import datetime
from itertools import groupby
from typing import List, Set

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date

from django_ledger.io import roles
from django_ledger.io.ratios import FinancialRatioManager
from django_ledger.io.roles import RolesManager
from django_ledger.models.journalentry import JournalEntryModel
from django_ledger.models.journalentry import validate_activity

UserModel = get_user_model()


class LazyImporter:
    """
    This class eliminates the circle dependency between models.
    """
    ENTITY_MODEL = None
    LEDGER_MODEL = None
    TXS_MODEL = None

    def get_entity_model(self):
        if not self.ENTITY_MODEL:
            from django_ledger.models.entity import EntityModel
            self.ENTITY_MODEL = EntityModel
        return self.ENTITY_MODEL

    def get_txs_model(self):
        if not self.TXS_MODEL:
            from django_ledger.models.transactions import TransactionModel
            self.TXS_MODEL = TransactionModel
        return self.TXS_MODEL

    def get_ledger_model(self):
        if not self.LEDGER_MODEL:
            from django_ledger.models.ledger import LedgerModel
            self.LEDGER_MODEL = LedgerModel
        return self.LEDGER_MODEL


lazy_importer = LazyImporter()


def validate_tx_data(tx_data: list):
    credits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'credit')
    debits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'debit')
    is_valid = credits == debits
    if not is_valid:
        raise ValidationError(f'Invalid tx data. Credits and debits must match. Currently cr: {credits}, db {debits}.')
    return is_valid


def validate_dates(from_date: str or datetime = None, to_date: str or datetime = None):
    if from_date and not isinstance(from_date, datetime):
        from_date = parse_date(from_date)
    if to_date and not isinstance(to_date, datetime):
        to_date = parse_date(to_date)
    return from_date, to_date


class IOMixIn:
    """
    Controls how transactions are recorded into the ledger.
    """

    # used in migrate_states...
    def commit_txs(self,
                   je_date: str or datetime,
                   je_txs: list,
                   je_activity: str,
                   je_posted: bool = False,
                   je_ledger=None,
                   je_desc=None,
                   je_origin=None,
                   je_parent=None):
        """
        Creates JE from TXS list using provided account_id.

        TXS = List[{
            'account_id': Account Database UUID
            'tx_type': credit/debit,
            'amount': Decimal/Float/Integer,
            'description': string,
            'staged_tx_model': StagedTransactionModel or None
        }]

        :param je_date:
        :param je_txs:
        :param je_activity:
        :param je_posted:
        :param je_ledger:
        :param je_desc:
        :param je_origin:
        :param je_parent:
        :return:
        """
        # Validates that credits/debits balance.
        validate_tx_data(je_txs)

        # Validates that the activity is valid.
        je_activity = validate_activity(je_activity)

        if all([isinstance(self, lazy_importer.get_entity_model()),
                not je_ledger]):
            raise ValidationError('Must pass an instance of LedgerModel')

        if not je_ledger:
            je_ledger = self

        je_model = JournalEntryModel.objects.create(
            ledger=je_ledger,
            description=je_desc,
            date=je_date,
            origin=je_origin,
            activity=je_activity,
            posted=je_posted,
            parent=je_parent
        )

        TransactionModel = lazy_importer.get_txs_model()
        txs_models = [
            TransactionModel(
                account_id=tx['account_id'],
                tx_type=tx['tx_type'],
                amount=tx['amount'],
                description=tx['description'],
                journal_entry=je_model,
                stagedtransactionmodel=tx.get('staged_tx_model')
            ) for tx in je_txs
        ]
        txs_models = TransactionModel.objects.bulk_create(txs_models)
        return je_model, txs_models

    def get_txs_queryset(self,
                         user_model: UserModel,
                         to_date: str or datetime = None,
                         from_date: str or datetime = None,
                         year: int = None,
                         activity: str = None,
                         role: str = None,
                         accounts: str or List[str] or Set[str] = None,
                         posted: bool = True,
                         exclude_zero_bal: bool = True,
                         by_period: bool = False):

        activity = validate_activity(activity)
        role = roles.validate_roles(role)
        from_date, to_date = validate_dates(from_date, to_date)

        TransactionModel = lazy_importer.get_txs_model()

        # If IO is on entity model....
        if isinstance(self, lazy_importer.get_entity_model()):
            txs_qs = TransactionModel.objects.for_entity(
                user_model=user_model,
                entity_model=self
            )

        # If IO is on ledger model....
        elif isinstance(self, lazy_importer.get_ledger_model()):
            txs_qs = TransactionModel.objects.for_ledger(
                user_model=user_model,
                ledger_model=self
            )
        else:
            txs_qs = TransactionModel.objects.none()

        if exclude_zero_bal:
            txs_qs = txs_qs.filter(amount__gt=0)

        if posted:
            txs_qs = txs_qs.posted()

        if from_date:
            txs_qs = txs_qs.from_date(from_date=from_date)

        if to_date:
            txs_qs = txs_qs.to_date(to_date=to_date)

        if year:
            txs_qs = txs_qs.for_year(year)

        if accounts:
            if not isinstance(accounts, str):
                accounts = [accounts]
            txs_qs = txs_qs.for_accounts(account_list=accounts)

        if activity:
            if isinstance(activity, str):
                activity = [activity]
            txs_qs = txs_qs.for_activity(activity_list=activity)
        if role:
            if isinstance(role, str):
                role = [role]
            txs_qs = txs_qs.for_roles(role_list=role)

        txs_qs = txs_qs.values(
            'account__uuid',
            'account__balance_type',
            'tx_type',
            'account__code',
            'account__name',
            'account__role',
        )

        if by_period:
            txs_qs = txs_qs.annotate(
                balance=Sum('amount'),
                dt_idx=TruncMonth('journal_entry__date'),
            ).order_by('journal_entry__date', 'account__uuid')
        else:
            txs_qs = txs_qs.annotate(
                balance=Sum('amount'),
            ).order_by('account__uuid')
        return txs_qs

    def get_jes(self,
                user: UserModel,
                to_date: str = None,
                from_date: str = None,
                year: str = None,
                equity_only: bool = False,
                activity: str = None,
                role: str = None,
                accounts: set = None,
                signs: bool = False,
                by_period: bool = False) -> list:

        if equity_only:
            role = roles.GROUP_EARNINGS

        je_txs = self.get_txs_queryset(
            user_model=user,
            to_date=to_date,
            from_date=from_date,
            year=year,
            activity=activity,
            role=role,
            accounts=accounts,
            by_period=by_period)

        # reverts the amount sign if the tx_type does not match the account_type prior to aggregating balances.
        for tx in je_txs:
            if tx['account__balance_type'] != tx['tx_type']:
                tx['balance'] = -tx['balance']

        accounts_gb_code = groupby(je_txs, key=lambda a: (
            a['account__uuid'],
            a.get('dt_idx').year if by_period else None,
            a.get('dt_idx').month if by_period else None,
        ))

        gb_digest = list()
        for k, g in accounts_gb_code:
            gl = list(g)
            gb_digest.append({
                'account_uuid': k[0],
                'period_year': k[1],
                'period_month': k[2],
                'role_bs': roles.BS_ROLES.get(gl[0]['account__role']),
                'role': gl[0]['account__role'],
                'code': gl[0]['account__code'],
                'name': gl[0]['account__name'],
                'balance_type': gl[0]['account__balance_type'],
                'balance': sum(a['balance'] for a in gl),
                'account_list': gl
            })

        if signs:
            for acc in gb_digest:
                if any([
                    all([acc['role_bs'] == 'assets',
                         acc['balance_type'] == 'credit']),
                    all([acc['role_bs'] in ('liabilities', 'equity', 'other'),
                         acc['balance_type'] == 'debit'])
                ]):
                    acc['balance'] = -acc['balance']
        return gb_digest

    def digest(self,
               user_model: UserModel,
               accounts: set = None,
               activity: str = None,
               signs: bool = True,
               to_date: str = None,
               from_date: str = None,
               year: int = None,
               process_roles: bool = True,
               process_groups: bool = False,
               process_ratios: bool = False,
               equity_only: bool = False,
               by_period: bool = False) -> dict:

        accounts_digest = self.get_jes(
            user=user_model,
            accounts=accounts,
            activity=activity,
            to_date=to_date,
            from_date=from_date,
            year=year,
            signs=signs,
            equity_only=equity_only,
            by_period=by_period
        )

        digest = dict(
            accounts=accounts_digest
        )

        if process_roles or process_groups:
            roles_mgr = RolesManager(
                tx_digest=digest,
                roles=process_roles,
                groups=process_groups,
                by_period=by_period)
            digest = roles_mgr.generate()

        if process_ratios:
            ratio_gen = FinancialRatioManager(tx_digest=digest)
            digest = ratio_gen.generate()

        return {
            'tx_digest': digest,
        }
