"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import datetime, date
from itertools import groupby
from random import choice
from typing import List, Set, Union, Tuple

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum, QuerySet
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import localdate, make_aware, is_naive

from django_ledger.exceptions import InvalidDateInputError, TransactionNotInBalanceError
from django_ledger.io import roles
from django_ledger.io.ratios import FinancialRatioManager
from django_ledger.io.roles import RoleManager, GroupManager, BS_ASSET_ROLE, BS_LIABILITIES_ROLE, BS_EQUITY_ROLE
from django_ledger.models.utils import LazyLoader
from django_ledger.settings import (DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE,
                                    DJANGO_LEDGER_TRANSACTION_CORRECTION)

UserModel = get_user_model()

lazy_importer = LazyLoader()


def diff_tx_data(tx_data: list, raise_exception: bool = True):
    IS_TX_MODEL = False
    TransactionModel = lazy_importer.get_txs_model()

    if isinstance(tx_data[0], TransactionModel):
        CREDITS = sum(tx.amount for tx in tx_data if tx.tx_type == 'credit')
        DEBITS = sum(tx.amount for tx in tx_data if tx.tx_type == 'debit')
        IS_TX_MODEL = True
    elif isinstance(tx_data[0], dict):
        CREDITS = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'credit')
        DEBITS = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'debit')
    else:
        raise ValidationError('Only Dictionary or TransactionModel allowed.')

    is_valid = (CREDITS == DEBITS)
    diff = CREDITS - DEBITS

    if not is_valid and abs(diff) > DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE:
        if raise_exception:
            raise TransactionNotInBalanceError(
                f'Invalid tx data. Credits and debits must match. Currently cr: {CREDITS}, db {DEBITS}.'
                f'Max Tolerance {DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE}'
            )

    return IS_TX_MODEL, is_valid, diff


def balance_tx_data(tx_data: list, perform_correction: bool = True) -> bool:
    if tx_data:

        IS_TX_MODEL, is_valid, diff = diff_tx_data(tx_data, raise_exception=perform_correction)

        if not perform_correction and abs(diff) > DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE:
            return False

        while not is_valid:

            tx_type_choice = choice(['debit', 'credit'])
            txs_candidates = list(tx for tx in tx_data if tx.tx_type == tx_type_choice)
            if len(txs_candidates) > 0:
                tx = choice(list(tx for tx in tx_data if tx.tx_type == tx_type_choice))

                if any([diff > 0 and tx_type_choice == 'debit',
                        diff < 0 and tx_type_choice == 'credit']):
                    if IS_TX_MODEL:
                        tx.amount += DJANGO_LEDGER_TRANSACTION_CORRECTION
                    else:
                        tx['amount'] += DJANGO_LEDGER_TRANSACTION_CORRECTION

                elif any([diff < 0 and tx_type_choice == 'debit',
                          diff > 0 and tx_type_choice == 'credit']):
                    if IS_TX_MODEL:
                        tx.amount -= DJANGO_LEDGER_TRANSACTION_CORRECTION
                    else:
                        tx['amount'] += DJANGO_LEDGER_TRANSACTION_CORRECTION

                IS_TX_MODEL, is_valid, diff = diff_tx_data(tx_data)

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
                raise InvalidDateInputError(
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
        from_date: Union[str, datetime, date] = None,
        to_date: Union[str, datetime, date] = None) -> Tuple[date, date]:
    from_date = validate_io_date(from_date, no_parse_locadate=False)
    to_date = validate_io_date(to_date)
    return from_date, to_date


def validate_activity(activity: str, raise_404: bool = False):
    if activity:
        JournalEntryModel = lazy_importer.get_journal_entry_model()
        if activity in JournalEntryModel.ACTIVITY_IGNORE:
            activity = None

        # todo: temporary fix. User should be able to pass a list.
        if isinstance(activity, list) and len(activity) == 1:
            activity = activity[0]
        elif isinstance(activity, list) and len(activity) > 1:
            exception = ValidationError(f'Multiple activities passed {activity}')
            if raise_404:
                raise Http404(exception)
            raise exception

        valid = activity in JournalEntryModel.ACTIVITY_ALLOWS
        if activity and not valid:
            exception = ValidationError(f'{activity} is invalid. Choices are {JournalEntryModel.ACTIVITY_ALLOWS}.')
            if raise_404:
                raise Http404(exception)
            raise exception

    return activity


class IOError(ValidationError):
    pass


class IOMixIn:
    """
    Controls how transactions are recorded into the ledger.
    """

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
                        by_activity: bool = False,
                        by_tx_type: bool = False,
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
                        entity_slug=self
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
        ]
        ANNOTATE = {'balance': Sum('amount')}
        ORDER_BY = ['account__uuid']

        if by_period:
            ORDER_BY.append('journal_entry__date')
            ANNOTATE['dt_idx'] = TruncMonth('journal_entry__date')

        if by_unit:
            VALUES += ['journal_entry__entity_unit__uuid', 'journal_entry__entity_unit__name']
            ORDER_BY.append('journal_entry__entity_unit__uuid')

        if by_activity:
            VALUES.append('journal_entry__activity')
            ORDER_BY.append('journal_entry__activity')

        if by_tx_type:
            VALUES.append('tx_type')
            ORDER_BY.append('tx_type')

        return txs_qs.values(*VALUES).annotate(**ANNOTATE).order_by(*ORDER_BY)

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
                      absolute_balances: bool = False,
                      by_unit: bool = False,
                      by_activity: bool = False,
                      by_tx_type: bool = False,
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
            by_activity=by_activity,
            by_tx_type=by_tx_type,
            by_period=by_period)

        if not absolute_balances:
            # reverts the amount sign if the tx_type does not match the account_type prior to aggregating balances.
            for tx in txs_qs:
                if tx['account__balance_type'] != tx['tx_type']:
                    tx['balance'] = -tx['balance']

        accounts_gb_code = groupby(txs_qs,
                                   key=lambda a: (
                                       a['account__uuid'],
                                       a.get('journal_entry__entity_unit__uuid'),
                                       a.get('dt_idx').year if by_period else None,
                                       a.get('dt_idx').month if by_period else None,
                                       a.get('journal_entry__activity'),
                                       a.get('tx_type'),
                                   ))

        gb_digest = [
            self.digest_gb_accounts(k, g) for k, g in accounts_gb_code
        ]

        if signs and not absolute_balances:
            TransactionModel = lazy_importer.get_txs_model()
            for acc in gb_digest:
                if any([
                    all([acc['role_bs'] == BS_ASSET_ROLE,
                         acc['balance_type'] == TransactionModel.CREDIT]),
                    all([acc['role_bs'] in (BS_LIABILITIES_ROLE, BS_EQUITY_ROLE),
                         acc['balance_type'] == TransactionModel.DEBIT])
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
               absolute_balances: bool = False,
               to_date: Union[str, datetime, date] = None,
               from_date: Union[str, datetime, date] = None,
               queryset: QuerySet = None,
               process_roles: bool = True,
               process_groups: bool = False,
               process_ratios: bool = False,
               equity_only: bool = False,
               by_period: bool = False,
               by_unit: bool = False,
               by_activity: bool = False,
               by_tx_type: bool = False,
               digest_name: str = None
               ) -> dict or tuple:

        if signs and absolute_balances:
            raise IOError('Cannot request signs and absolute balances concurrently.')

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
            absolute_balances=absolute_balances,
            equity_only=equity_only,
            by_period=by_period,
            by_unit=by_unit,
            by_activity=by_activity,
            by_tx_type=by_tx_type
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

        if not digest_name:
            digest_name = 'tx_digest'

        digest_results = {
            digest_name: digest,
        }

        return txs_qs, digest_results

    def commit_txs(self,
                   je_date: Union[str, datetime, date],
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
        balance_tx_data(je_txs)

        # Validates that the activity is valid.
        je_activity = validate_activity(je_activity)

        if all([
            isinstance(self, lazy_importer.get_entity_model()),
            not je_ledger
        ]):
            raise ValidationError('Must pass an instance of LedgerModel')

        if not je_ledger:
            je_ledger = self

        JournalEntryModel = lazy_importer.get_journal_entry_model()

        je_model = JournalEntryModel.on_coa.create(
            ledger=je_ledger,
            description=je_desc,
            date=je_date,
            origin=je_origin,
            activity=je_activity,
            parent=je_parent
        )

        # verify is False, no transactions are present yet....
        je_model.clean(verify=False)

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

        je_model.save(verify=True, post_on_verify=je_posted)
        return je_model, txs_models

    @staticmethod
    def digest_gb_accounts(k, g):
        gl = list(g)
        return {
            'account_uuid': k[0],
            'unit_uuid': k[1],
            'unit_name': gl[0].get('journal_entry__entity_unit__name'),
            'activity': gl[0].get('journal_entry__activity'),
            'period_year': k[2],
            'period_month': k[3],
            'role_bs': roles.BS_ROLES.get(gl[0]['account__role']),
            'role': gl[0]['account__role'],
            'code': gl[0]['account__code'],
            'name': gl[0]['account__name'],
            'balance_type': gl[0]['account__balance_type'],
            'tx_type': gl[0].get('tx_type'),
            'balance': sum(a['balance'] for a in gl),
        }
