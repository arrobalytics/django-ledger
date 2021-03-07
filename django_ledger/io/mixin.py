"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import datetime, date
from itertools import groupby
from typing import List, Set
from typing import Tuple

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum, QuerySet
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import localdate
from django.utils.timezone import make_aware, is_naive
from jsonschema import validate

from django_ledger.exceptions import InvalidDateInputException
from django_ledger.io import roles
from django_ledger.io.ratios import FinancialRatioManager
from django_ledger.io.roles import RoleManager, GroupManager
from django_ledger.models.journalentry import JournalEntryModel, validate_activity
from django_ledger.models.schemas import SCHEMA_DIGEST
from django_ledger.settings import DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME

UserModel = get_user_model()


class LazyImporter:
    """
    This class eliminates the circle dependency between models.
    """
    ENTITY_MODEL = None
    UNIT_MODEL = None
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

    def get_unit_model(self):
        if not self.UNIT_MODEL:
            from django_ledger.models.unit import EntityUnitModel
            self.UNIT_MODEL = EntityUnitModel
        return self.UNIT_MODEL


lazy_importer = LazyImporter()


def validate_tx_data(tx_data: list):
    if tx_data:
        TransactionModel = lazy_importer.get_txs_model()
        if isinstance(tx_data[0], TransactionModel):
            credits = sum(tx.amount for tx in tx_data if tx.tx_type == 'credit')
            debits = sum(tx.amount for tx in tx_data if tx.tx_type == 'debit')
        else:
            credits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'credit')
            debits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'debit')

        is_valid = credits == debits

        if not is_valid:
            raise ValidationError(f'Invalid tx data. Credits and debits must match. Currently cr: {credits}, db {debits}.')
        return is_valid
    return True


def validate_io_date(dt: str or date or datetime, no_parse_locadate: bool = True):
    if isinstance(dt, date):
        return dt
    elif isinstance(dt, datetime):
        if is_naive(dt):
            return make_aware(dt).date
        return dt.date
    elif isinstance(dt, str):
        # try to parse a date object from string...
        fdt = parse_date(dt)
        if not fdt:
            # try to parse a datetime object from string...
            fdt = parse_datetime(dt)
            if not fdt:
                raise InvalidDateInputException(
                    message=f'Could not parse date from {dt}'
                )
            elif is_naive(fdt):
                return make_aware(fdt).date
            return fdt.date
        return fdt
    if no_parse_locadate:
        return localdate()
    return


def validate_dates(
        from_date: str or date or datetime = None,
        to_date: str or date or datetime = None) -> Tuple[date, date]:
    from_date = validate_io_date(from_date, no_parse_locadate=False)
    to_date = validate_io_date(to_date)
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

    @staticmethod
    def digest_gb_accounts(k, g):
        gl = list(g)
        return {
            'account_uuid': k[0],
            'unit_uuid': k[1],
            'period_year': k[2],
            'period_month': k[3],
            'role_bs': roles.BS_ROLES.get(gl[0]['account__role']),
            'role': gl[0]['account__role'],
            'code': gl[0]['account__code'],
            'name': gl[0]['account__name'],
            'balance_type': gl[0]['account__balance_type'],
            'balance': sum(a['balance'] for a in gl),
            'account_list': gl
        }

    def database_digest(self,
                        user_model: UserModel,
                        queryset: QuerySet,
                        from_date: str or datetime = None,
                        to_date: str or datetime = None,
                        activity: str = None,
                        role: str = None,
                        entity_slug: str = None,
                        unit_slug: str = None,
                        accounts: str or List[str] or Set[str] = None,
                        posted: bool = True,
                        exclude_zero_bal: bool = True,
                        by_period: bool = False,
                        by_unit: bool = False):

        activity = validate_activity(activity)
        role = roles.validate_roles(role)
        from_date, to_date = validate_dates(from_date, to_date)

        if not queryset:
            TransactionModel = lazy_importer.get_txs_model()

            # If IO is on entity model....
            if isinstance(self, lazy_importer.get_entity_model()):
                if unit_slug:
                    txs_qs = TransactionModel.objects.for_unit(
                        user_model=user_model,
                        entity_slug=entity_slug or self.slug,
                        unit_slug=unit_slug
                    )
                else:
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
            # If IO is on unit model....
            elif isinstance(self, lazy_importer.get_unit_model()):
                if not entity_slug:
                    raise ValidationError('Calling digest from Entity Unit requires entity_slug')
                txs_qs = TransactionModel.objects.for_unit(
                    user_model=user_model,
                    entity_slug=entity_slug,
                    unit_model=self
                )
            else:
                txs_qs = TransactionModel.objects.none()
        else:
            txs_qs = queryset

        if exclude_zero_bal:
            txs_qs = txs_qs.filter(amount__gt=0)

        if posted:
            txs_qs = txs_qs.posted()

        if from_date:
            txs_qs = txs_qs.from_date(from_date=from_date)

        if to_date:
            txs_qs = txs_qs.to_date(to_date=to_date)

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

        VALUES = [
            'account__uuid',
            'account__balance_type',
            'tx_type',
            'account__code',
            'account__name',
            'account__role',
            'journal_entry__entity_unit__uuid'
        ]

        txs_qs = txs_qs.values(*VALUES)

        if by_period:
            txs_qs = txs_qs.annotate(
                balance=Sum('amount'),
                dt_idx=TruncMonth('journal_entry__date'),
            ).order_by('journal_entry__date', 'account__uuid')
            if by_unit:
                txs_qs.order_by('journal_entry__date', 'account__uuid', 'journal_entry__entity_unit__uuid')
        elif by_unit:
            txs_qs = txs_qs.annotate(
                balance=Sum('amount'),
            ).order_by('account__uuid', 'journal_entry__entity_unit__uuid')
        else:
            txs_qs = txs_qs.annotate(
                balance=Sum('amount'),
            ).order_by('account__uuid')

        return txs_qs

    def python_digest(self,
                      user_model: UserModel,
                      queryset: QuerySet,
                      to_date: str = None,
                      from_date: str = None,
                      equity_only: bool = False,
                      activity: str = None,
                      entity_slug: str = None,
                      unit_slug: str = None,
                      role: str = None,
                      accounts: set = None,
                      signs: bool = False,
                      by_unit: bool = False,
                      by_period: bool = False) -> list or tuple:

        if equity_only:
            role = roles.GROUP_EARNINGS

        txs_qs = self.database_digest(
            user_model=user_model,
            queryset=queryset,
            to_date=to_date,
            from_date=from_date,
            entity_slug=entity_slug,
            unit_slug=unit_slug,
            activity=activity,
            role=role,
            accounts=accounts,
            by_unit=by_unit,
            by_period=by_period)

        # reverts the amount sign if the tx_type does not match the account_type prior to aggregating balances.
        for tx in txs_qs:
            if tx['account__balance_type'] != tx['tx_type']:
                tx['balance'] = -tx['balance']

        accounts_gb_code = groupby(txs_qs,
                                   key=lambda a: (
                                       a['account__uuid'],
                                       a['journal_entry__entity_unit__uuid'] if by_unit else None,
                                       a.get('dt_idx').year if by_period else None,
                                       a.get('dt_idx').month if by_period else None,
                                   ))

        gb_digest = [
            self.digest_gb_accounts(k, g) for k, g in accounts_gb_code
        ]

        if signs:
            for acc in gb_digest:
                if any([
                    all([acc['role_bs'] == 'assets',
                         acc['balance_type'] == 'credit']),
                    all([acc['role_bs'] in ('liabilities', 'equity', 'other'),
                         acc['balance_type'] == 'debit'])
                ]):
                    acc['balance'] = -acc['balance']

        return txs_qs, gb_digest

    def digest(self,
               user_model: UserModel,
               accounts: set or list = None,
               activity: str = None,
               entity_slug: str = None,
               unit_slug: str = None,
               signs: bool = True,
               to_date: str = None,
               from_date: str = None,
               queryset: QuerySet = None,
               process_roles: bool = True,
               process_groups: bool = False,
               process_ratios: bool = False,
               equity_only: bool = False,
               by_period: bool = False,
               by_unit: bool = True,
               return_queryset: bool = False,
               digest_name: str = None
               ) -> dict or tuple:

        txs_qs, accounts_digest = self.python_digest(
            queryset=queryset,
            user_model=user_model,
            accounts=accounts,
            activity=activity,
            entity_slug=entity_slug,
            unit_slug=unit_slug,
            to_date=to_date,
            from_date=from_date,
            signs=signs,
            equity_only=equity_only,
            by_period=by_period,
            by_unit=by_unit,
        )

        digest = dict(
            accounts=accounts_digest
        )

        if process_roles:
            roles_mgr = RoleManager(
                tx_digest=digest,
                by_period=by_period,
                by_unit=by_unit
            )
            digest = roles_mgr.digest()

        if process_groups:
            group_mgr = GroupManager(
                tx_digest=digest,
                by_period=by_period,
                by_unit=by_unit
            )
            digest = group_mgr.digest()

        if process_ratios:
            ratio_gen = FinancialRatioManager(tx_digest=digest)
            digest = ratio_gen.digest()

        if DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME:
            validate(instance=digest, schema=SCHEMA_DIGEST)

        if not digest_name:
            digest_name = 'tx_digest'

        digest_results = {
            digest_name: digest,
        }

        if return_queryset:
            return txs_qs, digest_results
        return digest_results
