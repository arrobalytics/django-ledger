"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from itertools import groupby
from pathlib import Path
from random import choice
from typing import List, Set, Union, Tuple, Optional, Dict
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Sum, QuerySet
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import make_aware, is_naive, localtime
from django.utils.translation import gettext_lazy as _

from django_ledger import settings
from django_ledger.exceptions import InvalidDateInputError, TransactionNotInBalanceError
from django_ledger.io import roles as roles_module
from django_ledger.io.io_context import (
    RoleContextManager, GroupContextManager, ActivityContextManager,
    BalanceSheetStatementContextManager, IncomeStatementContextManager,
    CashFlowStatementContextManager
)
from django_ledger.io.io_digest import IODigestContextManager
from django_ledger.io.ratios import FinancialRatioManager
from django_ledger.models.utils import lazy_loader

UserModel = get_user_model()


def diff_tx_data(tx_data: list, raise_exception: bool = True):
    IS_TX_MODEL = False
    TransactionModel = lazy_loader.get_txs_model()

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

    if not is_valid and abs(diff) > settings.DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE:
        if raise_exception:
            raise TransactionNotInBalanceError(
                f'Invalid tx data. Credits and debits must match. Currently cr: {CREDITS}, db {DEBITS}.'
                f'Max Tolerance {settings.DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE}'
            )

    return IS_TX_MODEL, is_valid, diff


def check_tx_balance(tx_data: list, perform_correction: bool = False) -> bool:
    if tx_data:

        IS_TX_MODEL, is_valid, diff = diff_tx_data(tx_data, raise_exception=perform_correction)

        if not perform_correction and abs(diff):
            return False

        if not perform_correction and abs(diff) > settings.DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE:
            return False

        while not is_valid:
            tx_type_choice = choice(['debit', 'credit'])
            txs_candidates = list(tx for tx in tx_data if tx['tx_type'] == tx_type_choice)
            if len(txs_candidates) > 0:
                tx = choice(list(tx for tx in tx_data if tx['tx_type'] == tx_type_choice))
                if any([diff > 0 and tx_type_choice == 'debit',
                        diff < 0 and tx_type_choice == 'credit']):
                    if IS_TX_MODEL:
                        tx.amount += settings.DJANGO_LEDGER_TRANSACTION_CORRECTION
                    else:
                        tx['amount'] += settings.DJANGO_LEDGER_TRANSACTION_CORRECTION

                elif any([diff < 0 and tx_type_choice == 'debit',
                          diff > 0 and tx_type_choice == 'credit']):
                    if IS_TX_MODEL:
                        tx.amount -= settings.DJANGO_LEDGER_TRANSACTION_CORRECTION
                    else:
                        tx['amount'] += settings.DJANGO_LEDGER_TRANSACTION_CORRECTION

                IS_TX_MODEL, is_valid, diff = diff_tx_data(tx_data)

    return True


def validate_io_date(
        dt: Union[str, date, datetime],
        no_parse_localdate: bool = True) -> Optional[Union[datetime, date]]:
    if not dt:
        return

    if isinstance(dt, date):
        # dt = make_aware(
        #     value=datetime.combine(
        #         dt,
        #         datetime.min.time()
        #     ),
        #     timezone=ZoneInfo('UTC')
        # )
        return dt

    elif isinstance(dt, datetime):
        if is_naive(dt):
            return make_aware(
                value=dt,
                timezone=ZoneInfo('UTC')
            )
        return dt

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
                fdt = make_aware(fdt)
        return fdt

    if no_parse_localdate:
        return localtime()


def validate_dates(
        from_date: Union[str, datetime, date] = None,
        to_date: Union[str, datetime, date] = None) -> Tuple[date, date]:
    from_date = validate_io_date(from_date, no_parse_localdate=False)
    to_date = validate_io_date(to_date)
    return from_date, to_date


def validate_activity(activity: str, raise_404: bool = False):
    # idea: move to model???...
    JournalEntryModel = lazy_loader.get_journal_entry_model()
    valid = activity in JournalEntryModel.VALID_ACTIVITIES
    if activity and not valid:
        exception = ValidationError(f'{activity} is invalid. Choices are {JournalEntryModel.VALID_ACTIVITIES}.')
        if raise_404:
            raise Http404(exception)
        raise exception
    return activity


class IOValidationError(ValidationError):
    pass


@dataclass
class IOResult:
    """
    A carrier class to store IO digest information during the digest call.
    """
    # DB Aggregation...
    db_from_date: Optional[date] = None
    db_to_date: Optional[date] = None

    # Closing Entry lookup...
    ce_match: bool = False
    ce_from_date: Optional[date] = None
    ce_to_date: Optional[date] = None

    # the final queryset to evaluate...
    txs_queryset = None

    # the aggregated account balance...
    accounts_digest: Optional[List[Dict]] = None


class IODatabaseMixIn:
    """
    The main entry point to query DB for transactions. The database_digest method pushes as much load as possible
    to the Database so transactions are aggregated at the database layer and are not pulled into memory.
    This is important por performance purposes since Entities may have a large amount of transactions to be
    aggregated.

    The python_digest method aggregates and processes the raw data stored in the database and applies accounting
    rules to stored transactions.

    This method also makes use of Closing Entries whenever possible to minimize the amount of data to aggregate
    during a specific call. Closing Entries can be considered "checkpoints", which create materialized aggregation
    of transactions for commonly used dates. (i.e. Fiscal Year End, Month End, Quarter End, etc.). This approach
    helps minimize the number of transactions to aggregate for a given request.
    """

    def is_entity_model(self):
        return isinstance(self, lazy_loader.get_entity_model())

    def is_ledger_model(self):
        return isinstance(self, lazy_loader.get_ledger_model())

    def is_entity_unit_model(self):
        return isinstance(self, lazy_loader.get_unit_model())

    def get_entity_model_from_io(self):
        if self.is_entity_model():
            return self
        elif self.is_ledger_model():
            return self.entity
        elif self.is_entity_unit_model():
            return self.entity

    def database_digest(self,
                        entity_slug: Optional[str] = None,
                        unit_slug: Optional[str] = None,
                        user_model: Optional[UserModel] = None,
                        from_date: Optional[Union[date, datetime]] = None,
                        to_date: Optional[Union[date, datetime]] = None,
                        by_activity: bool = False,
                        by_tx_type: bool = False,
                        by_period: bool = False,
                        by_unit: bool = False,
                        activity: Optional[str] = None,
                        role: str = Optional[str],
                        accounts: Optional[Union[str, List[str], Set[str]]] = None,
                        posted: bool = True,
                        exclude_zero_bal: bool = True,
                        force_closing_entry_use: bool = False
                        ) -> IOResult:
        """
        Performs the appropriate database aggregation query for a given request.


        Parameters
        ----------
        entity_slug: str
            EntityModel slug to use. If not provided it will be derived from the EntityModel instance.
            Will be validated against current EntityModel instance for safety. Defaults to None.
        unit_slug: str
            EntityUnitModel used to query transactions. If provided will be validated against current EntityModelUnit
            instance. Defaults to None.
        user_model: UserModel
            The django UserModel to validate against transaction ownership and permissions (i.e. Admin and Manager).
            Defaults to None.
        from_date: date or datetime
            Stating date or datetime to query from (inclusive).
        to_date: date or datetime
            End date or datetime to query to (inclusive).
        activity: str
            Filters transactions to match specific activity. Defaults to None.
        role: str
            Filters transactions to match specific role. Defaults to None.
        accounts: str or List[str] ot Set[str]
            Optional list of accounts to query. Defaults to None (all).
        posted: bool
            Consider only posted transactions. Defaults to True.
        exclude_zero_bal: bool
            Excludes transactions with zero balance, if any.
        by_activity: bool
            Returns results aggregated by activity if needed. Defaults to False.
        by_tx_type: bool
            Returns results aggregated by DEBIT/CREDIT if needed. Defaults to False.
        by_period: bool
            Returns results aggregated by accounting if needed. Defaults to False.
        by_unit: bool
            Returns results aggregated by unit if needed. Defaults to False.
        force_closing_entry_use: bool
            Forces the use of closing entries if DJANGO_LEDGER_USE_CLOSING_ENTRIES setting is set to False.
        Returns
        -------
        IOResult
        """

        TransactionModel = lazy_loader.get_txs_model()
        io_result = IOResult(db_to_date=to_date, db_from_date=from_date)
        txs_queryset_closing_entry = TransactionModel.objects.none()

        # where the IO model is operating from??...
        if self.is_entity_model():
            if entity_slug:
                if entity_slug != self.slug:
                    raise IOValidationError('Inconsistent entity_slug. '
                                            f'Provided {entity_slug} does not match actual {self.slug}')
            if unit_slug:
                txs_queryset = TransactionModel.objects.for_unit(
                    user_model=user_model,
                    entity_slug=entity_slug or self.slug,
                    unit_slug=unit_slug
                )
            else:
                txs_queryset = TransactionModel.objects.for_entity(
                    user_model=user_model,
                    entity_slug=self
                )
        elif self.is_ledger_model():
            if not entity_slug:
                raise IOValidationError(
                    'Calling digest from Ledger Model requires entity_slug explicitly for safety')
            txs_queryset = TransactionModel.objects.for_ledger(
                user_model=user_model,
                entity_slug=entity_slug,
                ledger_model=self
            )
        elif self.is_entity_unit_model():
            if not entity_slug:
                raise IOValidationError(
                    'Calling digest from Entity Unit requires entity_slug explicitly for safety')
            txs_queryset = TransactionModel.objects.for_unit(
                user_model=user_model,
                entity_slug=entity_slug,
                unit_slug=unit_slug or self
            )
        else:
            txs_queryset = TransactionModel.objects.none()

        # use closing entries to minimize DB aggregation if activated...
        if settings.DJANGO_LEDGER_USE_CLOSING_ENTRIES or force_closing_entry_use:
            entity_model = self.get_entity_model_from_io()

            # looking up available dates...
            ce_from_date = entity_model.get_closing_entry_for_date(io_date=from_date, inclusive=False)
            ce_to_date = entity_model.get_closing_entry_for_date(io_date=to_date)

            # unbounded lookup, no date match
            # finding the closest closing entry to aggregate from if present...
            if not from_date and not ce_to_date:
                ce_alt_from_date = entity_model.get_nearest_next_closing_entry(io_date=to_date)

                # if there's a suitable closing entry...
                if ce_alt_from_date:
                    txs_queryset_closing_entry = txs_queryset.is_closing_entry().filter(
                        journal_entry__timestamp__date=ce_alt_from_date
                    )
                    io_result.ce_match = True
                    io_result.ce_from_date = ce_alt_from_date
                    # limit db aggregation to unclosed entries...
                    io_result.db_from_date = ce_alt_from_date + timedelta(days=1)
                    io_result.db_to_date = to_date
                    # print(f'Unbounded lookup no date match. Closest from_dt: {ce_alt_from_date}...')

            # unbounded lookup, exact to_date match...
            elif not ce_from_date and ce_to_date:
                txs_queryset_closing_entry = txs_queryset.is_closing_entry().filter(
                    journal_entry__timestamp__date=ce_to_date)
                io_result.ce_match = True
                io_result.ce_to_date = ce_to_date

                # no need to DB aggregate...
                io_result.db_from_date = None
                io_result.db_to_date = None
                # print(f'Unbounded lookup EXACT date match. Closest to_dt: {ce_to_date}...')

            # bounded exact from_date and to_date match...
            elif ce_from_date and ce_to_date:
                txs_queryset_closing_entry = txs_queryset.is_closing_entry().filter(
                    journal_entry__timestamp__date__in=[
                        ce_from_date,
                        ce_to_date
                    ])
                io_result.ce_match = True
                io_result.ce_from_date = ce_from_date
                io_result.ce_to_date = ce_to_date

                # no need to aggregate...
                io_result.db_from_date = None
                io_result.db_to_date = None
                # print(f'Bounded lookup EXACT date match. Closest from_dt: {ce_from_date} '
                #       f'| to_dt: {ce_to_date}...')

            # no suitable closing entries to use...
            else:
                txs_queryset = txs_queryset.not_closing_entry()
        else:
            # not using closing entries...
            txs_queryset = txs_queryset.not_closing_entry()

        if io_result.db_from_date:
            txs_queryset = txs_queryset.from_date(from_date=io_result.db_from_date)

        if io_result.db_to_date:
            txs_queryset = txs_queryset.to_date(to_date=io_result.db_to_date)

        if exclude_zero_bal:
            txs_queryset = txs_queryset.filter(amount__gt=0.00)

        if posted:
            txs_queryset = txs_queryset.posted()

        if accounts:
            if not isinstance(accounts, str):
                accounts = [accounts]
            txs_queryset = txs_queryset.for_accounts(account_list=accounts)

        if activity:
            if isinstance(activity, str):
                activity = [activity]
            txs_queryset = txs_queryset.for_activity(activity_list=activity)

        if role:
            txs_queryset = txs_queryset.for_roles(role_list=role)

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

        if by_unit:
            ORDER_BY.append('journal_entry__entity_unit__uuid')
            VALUES += ['journal_entry__entity_unit__uuid', 'journal_entry__entity_unit__name']

        if by_period:
            ORDER_BY.append('journal_entry__timestamp')
            ANNOTATE['dt_idx'] = TruncMonth('journal_entry__timestamp')

        if by_activity:
            ORDER_BY.append('journal_entry__activity')
            VALUES.append('journal_entry__activity')

        if by_tx_type:
            ORDER_BY.append('tx_type')
            VALUES.append('tx_type')

        txs_queryset = txs_queryset | txs_queryset_closing_entry

        io_result.txs_queryset = txs_queryset.values(*VALUES).annotate(**ANNOTATE).order_by(*ORDER_BY)
        return io_result

    def python_digest(self,
                      user_model: Optional[UserModel] = None,
                      entity_slug: Optional[str] = None,
                      unit_slug: Optional[str] = None,
                      to_date: Optional[Union[date, datetime, str]] = None,
                      from_date: Optional[Union[date, datetime, str]] = None,
                      equity_only: bool = False,
                      activity: str = None,
                      role: Optional[Union[Set[str], List[str]]] = None,
                      accounts: Optional[Union[Set[str], List[str]]] = None,
                      signs: bool = True,
                      by_unit: bool = False,
                      by_activity: bool = False,
                      by_tx_type: bool = False,
                      by_period: bool = False,
                      force_closing_entry_use: bool = False,
                      force_queryset_sorting: bool = False,
                      **kwargs) -> IOResult:
        """
        Performs the appropriate transaction post-processing after DB aggregation..


        Parameters
        ----------
        entity_slug: str
            EntityModel slug to use. If not provided it will be derived from the EntityModel instance.
            Will be validated against current EntityModel instance for safety. Defaults to None.
        unit_slug: str
            EntityUnitModel used to query transactions. If provided will be validated against current EntityModelUnit
            instance. Defaults to None.
        user_model: UserModel
            The django UserModel to validate against transaction ownership and permissions (i.e. Admin and Manager).
            Defaults to None.
        from_date: date or datetime
            Stating date or datetime to query from (inclusive).
        to_date: date or datetime
            End date or datetime to query to (inclusive).
        activity: str
            Filters transactions to match specific activity. Defaults to None.
        role: str
            Filters transactions to match specific role. Defaults to None.
        accounts: str or List[str] ot Set[str]
            Optional list of accounts to query. Defaults to None (all).
        by_activity: bool
            Returns results aggregated by activity if needed. Defaults to False.
        by_tx_type: bool
            Returns results aggregated by DEBIT/CREDIT if needed. Defaults to False.
        by_period: bool
            Returns results aggregated by accounting if needed. Defaults to False.
        by_unit: bool
            Returns results aggregated by unit if needed. Defaults to False.
        equity_only: bool
            Performs aggregation only on accounts that impact equity only (i.e. Income Statement Generation).
            Avoids unnecessary inclusion of accounts not relevant to what's needed.
        signs: bool
            Changes the balance of an account to negative if it represents a "negative" for display purposes.
            (i.e. Expense accounts will show balance as negative and Income accounts as positive.)
        force_closing_entry_use: bool
            Forces the use of closing entries if DJANGO_LEDGER_USE_CLOSING_ENTRIES setting is set to False.
        force_queryset_sorting: bool
            Forces sorting of the TransactionModelQuerySet before aggregation balances.
            Defaults to false.

        Returns
        -------
        IOResult
        """

        if equity_only:
            role = roles_module.GROUP_EARNINGS

        io_result = self.database_digest(
            user_model=user_model,
            entity_slug=entity_slug,
            unit_slug=unit_slug,
            to_date=to_date,
            from_date=from_date,
            by_unit=by_unit,
            by_activity=by_activity,
            by_tx_type=by_tx_type,
            by_period=by_period,
            activity=activity,
            role=role,
            accounts=accounts,
            force_closing_entry_use=force_closing_entry_use,
            **kwargs)

        for tx_model in io_result.txs_queryset:
            if tx_model['account__balance_type'] != tx_model['tx_type']:
                tx_model['balance'] = -tx_model['balance']

        gb_key = lambda a: (
            a['account__uuid'],
            a.get('journal_entry__entity_unit__uuid') if by_unit else None,
            a.get('dt_idx').year if by_period else None,
            a.get('dt_idx').month if by_period else None,
            a.get('journal_entry__activity') if by_activity else None,
            a.get('tx_type') if by_tx_type else None,
        )

        if force_queryset_sorting:
            io_result.txs_queryset = list(io_result.txs_queryset)
            io_result.txs_queryset.sort(key=gb_key)

        accounts_gb_code = groupby(io_result.txs_queryset, key=gb_key)
        accounts_digest = [self.aggregate_balances(k, g) for k, g in accounts_gb_code]

        for acc in accounts_digest:
            acc['balance_abs'] = abs(acc['balance'])

        if signs:
            TransactionModel = lazy_loader.get_txs_model()
            for acc in accounts_digest:
                if any([
                    all([acc['role_bs'] == roles_module.BS_ASSET_ROLE,
                         acc['balance_type'] == TransactionModel.CREDIT]),
                    all([acc['role_bs'] in (
                            roles_module.BS_LIABILITIES_ROLE,
                            roles_module.BS_EQUITY_ROLE
                    ),
                         acc['balance_type'] == TransactionModel.DEBIT])
                ]):
                    acc['balance'] = -acc['balance']

        io_result.accounts_digest = accounts_digest
        return io_result

    @staticmethod
    def aggregate_balances(k, g):
        gl = list(g)
        return {
            'account_uuid': k[0],
            'unit_uuid': k[1],
            'unit_name': gl[0].get('journal_entry__entity_unit__name'),
            'activity': gl[0].get('journal_entry__activity'),
            'period_year': k[2],
            'period_month': k[3],
            'role_bs': roles_module.BS_ROLES.get(gl[0]['account__role']),
            'role': gl[0]['account__role'],
            'code': gl[0]['account__code'],
            'name': gl[0]['account__name'],
            'balance_type': gl[0]['account__balance_type'],
            'tx_type': k[5],
            'balance': sum(a['balance'] for a in gl),
        }

    def digest(self,
               entity_slug: Optional[str] = None,
               unit_slug: Optional[str] = None,
               to_date: Optional[Union[date, datetime, str]] = None,
               from_date: Optional[Union[date, datetime, str]] = None,
               user_model: Optional[UserModel] = None,
               accounts: Optional[Union[Set[str], List[str]]] = None,
               role: Optional[Union[Set[str], List[str]]] = None,
               activity: Optional[str] = None,
               signs: bool = True,
               process_roles: bool = False,
               process_groups: bool = False,
               process_ratios: bool = False,
               process_activity: bool = False,
               equity_only: bool = False,
               by_period: bool = False,
               by_unit: bool = False,
               by_activity: bool = False,
               by_tx_type: bool = False,
               balance_sheet_statement: bool = False,
               income_statement: bool = False,
               cash_flow_statement: bool = False,
               **kwargs) -> IODigestContextManager:

        if balance_sheet_statement:
            from_date = None

        if cash_flow_statement:
            by_activity = True

        if activity:
            activity = validate_activity(activity)
        if role:
            role = roles_module.validate_roles(role)

        from_date, to_date = validate_dates(from_date, to_date)

        io_state = dict()
        io_state['io_model'] = self
        io_state['from_date'] = from_date
        io_state['to_date'] = to_date
        io_state['by_unit'] = by_unit
        io_state['unit_slug'] = unit_slug
        io_state['entity_slug'] = entity_slug
        io_state['by_period'] = by_period
        io_state['by_activity'] = by_activity
        io_state['by_tx_type'] = by_tx_type

        io_result = self.python_digest(
            user_model=user_model,
            accounts=accounts,
            role=role,
            activity=activity,
            entity_slug=entity_slug,
            unit_slug=unit_slug,
            to_date=to_date,
            from_date=from_date,
            signs=signs,
            equity_only=equity_only,
            by_period=by_period,
            by_unit=by_unit,
            by_activity=by_activity,
            by_tx_type=by_tx_type,
            **kwargs
        )

        io_state['io_result'] = io_result
        io_state['accounts'] = io_result.accounts_digest

        if process_roles:
            roles_mgr = RoleContextManager(
                io_data=io_state,
                by_period=by_period,
                by_unit=by_unit
            )

            # idea: change digest() name to something else? maybe aggregate, calculate?...
            io_state = roles_mgr.digest()

        if any([
            process_groups,
            balance_sheet_statement,
            income_statement,
            cash_flow_statement
        ]):
            group_mgr = GroupContextManager(
                io_data=io_state,
                by_period=by_period,
                by_unit=by_unit
            )
            io_state = group_mgr.digest()

            # todo: migrate this to group manager...
            io_state['group_account']['GROUP_ASSETS'].sort(
                key=lambda acc: roles_module.ROLES_ORDER_ASSETS.index(acc['role']))
            io_state['group_account']['GROUP_LIABILITIES'].sort(
                key=lambda acc: roles_module.ROLES_ORDER_LIABILITIES.index(acc['role']))
            io_state['group_account']['GROUP_CAPITAL'].sort(
                key=lambda acc: roles_module.ROLES_ORDER_CAPITAL.index(acc['role']))

        if process_ratios:
            ratio_gen = FinancialRatioManager(io_data=io_state)
            io_state = ratio_gen.digest()

        if process_activity:
            activity_manager = ActivityContextManager(io_data=io_state, by_unit=by_unit, by_period=by_period)
            activity_manager.digest()

        if balance_sheet_statement:
            balance_sheet_mgr = BalanceSheetStatementContextManager(io_data=io_state)
            io_state = balance_sheet_mgr.digest()

        if income_statement:
            income_statement_mgr = IncomeStatementContextManager(io_data=io_state)
            io_state = income_statement_mgr.digest()

        if cash_flow_statement:
            cfs = CashFlowStatementContextManager(io_data=io_state)
            io_state = cfs.digest()

        return IODigestContextManager(io_state=io_state)

    def commit_txs(self,
                   je_timestamp: Union[str, datetime, date],
                   je_txs: List[Dict],
                   je_posted: bool = False,
                   je_ledger_model=None,
                   je_unit_model=None,
                   je_desc=None,
                   je_origin=None,
                   force_je_retrieval: bool = False):
        """
        Creates JE from TXS list using provided account_id.

        TXS = List[{
            'account_id': Account Database UUID
            'tx_type': credit/debit,
            'amount': Decimal/Float/Integer,
            'description': string,
            'staged_tx_model': StagedTransactionModel or None
        }]

        :param je_timestamp:
        :param je_txs:
        :param je_activity:
        :param je_posted:
        :param je_ledger_model:
        :param je_desc:
        :param je_origin:
        :param je_parent:
        :return:
        """

        JournalEntryModel = lazy_loader.get_journal_entry_model()
        TransactionModel = lazy_loader.get_txs_model()

        # if isinstance(self, lazy_loader.get_entity_model()):

        # Validates that credits/debits balance.
        check_tx_balance(je_txs, perform_correction=False)
        je_timestamp = validate_io_date(dt=je_timestamp)

        # if calling from EntityModel must pass an instance of LedgerModel...
        if all([
            isinstance(self, lazy_loader.get_entity_model()),
            je_ledger_model is None
        ]):
            raise IOValidationError('Committing from EntityModel requires an instance of LedgerModel')

        # Validates that the provided LedgerModel id valid...
        if all([
            isinstance(self, lazy_loader.get_entity_model()),
            je_ledger_model is not None,
        ]):
            if je_ledger_model.entity_id != self.uuid:
                raise IOValidationError(f'LedgerModel {je_ledger_model} does not belong to {self}')

        # Validates that the provided EntityUnitModel id valid...
        if all([
            isinstance(self, lazy_loader.get_entity_model()),
            je_unit_model is not None,
        ]):
            if je_unit_model.entity_id != self.uuid:
                raise IOValidationError(f'EntityUnitModel {je_unit_model} does not belong to {self}')

        if not je_ledger_model:
            je_ledger_model = self

        if force_je_retrieval:
            try:
                if isinstance(je_timestamp, (datetime, str)):
                    je_model = je_ledger_model.journal_entries.get(timestamp__exact=je_timestamp)
                elif isinstance(je_timestamp, date):
                    je_model = je_ledger_model.journal_entries.get(timestamp__date__exact=je_timestamp)
                else:
                    raise IOValidationError(message=_(f'Invalid timestamp type {type(je_timestamp)}'))
            except ObjectDoesNotExist:
                raise IOValidationError(
                    message=_(f'Unable to retrieve Journal Entry model with Timestamp {je_timestamp}')
                )
        else:
            je_model = JournalEntryModel(
                ledger=je_ledger_model,
                entity_unit=je_unit_model,
                description=je_desc,
                timestamp=je_timestamp,
                origin=je_origin,
                posted=False,
                locked=False
            )
            je_model.save(verify=False)

        txs_models = [
            (
                TransactionModel(
                    account=txm_kwargs['account'],
                    amount=txm_kwargs['amount'],
                    tx_type=txm_kwargs['tx_type'],
                    description=txm_kwargs['description'],
                    journal_entry=je_model,
                ), txm_kwargs) for txm_kwargs in je_txs
        ]

        for tx, txm_kwargs in txs_models:
            staged_tx_model = txm_kwargs.get('staged_tx_model')
            if staged_tx_model:
                staged_tx_model.transaction_model = tx

        txs_models = je_model.transactionmodel_set.bulk_create(i[0] for i in txs_models)
        je_model.save(verify=True, post_on_verify=je_posted)
        return je_model, txs_models


class IOReportMixIn:
    PDF_REPORT_ORIENTATION = 'P'
    PDF_REPORT_MEASURE_UNIT = 'mm'
    PDF_REPORT_PAGE_SIZE = 'Letter'

    ReportTuple = namedtuple('ReportTuple',
                             field_names=[
                                 'balance_sheet_statement',
                                 'income_statement',
                                 'cash_flow_statement'
                             ])

    def digest_balance_sheet(self,
                             to_date: Union[date, datetime],
                             user_model: Optional[UserModel] = None,
                             txs_queryset: Optional[QuerySet] = None,
                             **kwargs: Dict) -> Union[IODigestContextManager, Tuple[QuerySet, Dict]]:
        return self.digest(
            user_model=user_model,
            to_date=to_date,
            balance_sheet_statement=True,
            txs_queryset=txs_queryset,
            as_io_digest=True,
            **kwargs
        )

    def get_balance_sheet_statement(self,
                                    to_date: Union[date, datetime],
                                    subtitle: Optional[str] = None,
                                    filepath: Optional[Path] = None,
                                    filename: Optional[str] = None,
                                    user_model: Optional[UserModel] = None,
                                    txs_queryset: Optional[QuerySet] = None,
                                    save_pdf: bool = False,
                                    **kwargs
                                    ):
        io_digest = self.digest_balance_sheet(
            to_date=to_date,
            user_model=user_model,
            txs_queryset=txs_queryset,
            **kwargs
        )

        report_klass = lazy_loader.get_balance_sheet_report_class()
        report = report_klass(
            self.PDF_REPORT_ORIENTATION,
            self.PDF_REPORT_MEASURE_UNIT,
            self.PDF_REPORT_PAGE_SIZE,
            io_digest=io_digest,
            report_subtitle=subtitle
        )
        if save_pdf:
            base_dir = Path(settings.BASE_DIR) if not filepath else Path(filepath)
            filename = report.get_pdf_filename() if not filename else filename
            filepath = base_dir.joinpath(filename)
            report.create_pdf_report()
            report.output(filepath)
        return report

    def digest_income_statement(self,
                                from_date: Union[date, datetime],
                                to_date: Union[date, datetime],
                                user_model: Optional[UserModel] = None,
                                txs_queryset: Optional[QuerySet] = None,
                                **kwargs) -> Union[IODigestContextManager, Tuple[QuerySet, Dict]]:
        return self.digest(
            user_model=user_model,
            from_date=from_date,
            to_date=to_date,
            income_statement=True,
            txs_queryset=txs_queryset,
            as_io_digest=True,
            **kwargs
        )

    def get_income_statement(self,
                             from_date: Union[date, datetime],
                             to_date: Union[date, datetime],
                             subtitle: Optional[str] = None,
                             filepath: Optional[Path] = None,
                             filename: Optional[str] = None,
                             user_model: Optional[UserModel] = None,
                             txs_queryset: Optional[QuerySet] = None,
                             save_pdf: bool = False,
                             **kwargs
                             ):
        io_digest = self.digest_income_statement(
            from_date=from_date,
            to_date=to_date,
            user_model=user_model,
            txs_queryset=txs_queryset,
            **kwargs
        )
        report_klass = lazy_loader.get_income_statement_report_class()
        report = report_klass(
            self.PDF_REPORT_ORIENTATION,
            self.PDF_REPORT_MEASURE_UNIT,
            self.PDF_REPORT_PAGE_SIZE,
            io_digest=io_digest,
            report_subtitle=subtitle
        )
        if save_pdf:
            base_dir = Path(settings.BASE_DIR) if not filepath else Path(filepath)
            filename = report.get_pdf_filename() if not filename else filename
            filepath = base_dir.joinpath(filename)
            report.create_pdf_report()
            report.output(filepath)
        return report

    def digest_cash_flow_statement(self,
                                   from_date: Union[date, datetime],
                                   to_date: Union[date, datetime],
                                   user_model: UserModel,
                                   txs_queryset: Optional[QuerySet] = None,
                                   **kwargs) -> Union[IODigestContextManager, Tuple[QuerySet, Dict]]:
        return self.digest(
            user_model=user_model,
            from_date=from_date,
            to_date=to_date,
            cash_flow_statement=True,
            txs_queryset=txs_queryset,
            as_io_digest=True,
            **kwargs
        )

    def get_cash_flow_statement(self,
                                from_date: Union[date, datetime],
                                to_date: Union[date, datetime],
                                subtitle: Optional[str] = None,
                                filepath: Optional[Path] = None,
                                filename: Optional[str] = None,
                                user_model: Optional[UserModel] = None,
                                txs_queryset: Optional[QuerySet] = None,
                                save_pdf: bool = False,
                                **kwargs):

        io_digest = self.digest_cash_flow_statement(
            from_date=from_date,
            to_date=to_date,
            user_model=user_model,
            txs_queryset=txs_queryset,
            **kwargs
        )

        report_klass = lazy_loader.get_cash_flow_statement_report_class()
        report = report_klass(
            self.PDF_REPORT_ORIENTATION,
            self.PDF_REPORT_MEASURE_UNIT,
            self.PDF_REPORT_PAGE_SIZE,
            io_digest=io_digest,
            report_subtitle=subtitle
        )
        if save_pdf:
            base_dir = Path(settings.BASE_DIR) if not filepath else Path(filepath)
            filename = report.get_pdf_filename() if not filename else filename
            filepath = base_dir.joinpath(filename)
            report.create_pdf_report()
            report.output(filepath)
        return report

    def get_financial_statements(self,
                                 from_date: Union[date, datetime],
                                 to_date: Union[date, datetime],
                                 dt_strfmt: str = '%Y%m%d',
                                 user_model: Optional[UserModel] = None,
                                 txs_queryset: Optional[QuerySet] = None,
                                 save_pdf: bool = False,
                                 filepath: Optional[Path] = None,
                                 **kwargs) -> ReportTuple:

        io_digest = self.digest(
            from_date=from_date,
            to_date=to_date,
            user_model=user_model,
            txs_queryset=txs_queryset,
            balance_sheet_statement=True,
            income_statement=True,
            cash_flow_statement=True,
            as_io_digest=True,
            **kwargs
        )

        bs_report_klass = lazy_loader.get_balance_sheet_report_class()
        bs_report = bs_report_klass(
            self.PDF_REPORT_ORIENTATION,
            self.PDF_REPORT_MEASURE_UNIT,
            self.PDF_REPORT_PAGE_SIZE,
            io_digest=io_digest
        )
        is_report_klass = lazy_loader.get_income_statement_report_class()
        is_report = is_report_klass(
            self.PDF_REPORT_ORIENTATION,
            self.PDF_REPORT_MEASURE_UNIT,
            self.PDF_REPORT_PAGE_SIZE,
            io_digest=io_digest
        )
        cfs_report_klass = lazy_loader.get_cash_flow_statement_report_class()
        cfs_report = cfs_report_klass(
            self.PDF_REPORT_ORIENTATION,
            self.PDF_REPORT_MEASURE_UNIT,
            self.PDF_REPORT_PAGE_SIZE,
            io_digest=io_digest
        )

        if save_pdf:
            base_dir = Path(settings.BASE_DIR) if not filepath else Path(filepath)
            bs_report.create_pdf_report()
            bs_report.output(base_dir.joinpath(bs_report.get_pdf_filename(dt_strfmt=dt_strfmt)))

            is_report.create_pdf_report()
            is_report.output(base_dir.joinpath(is_report.get_pdf_filename(from_dt=from_date, dt_strfmt=dt_strfmt)))

            cfs_report.create_pdf_report()
            cfs_report.output(base_dir.joinpath(cfs_report.get_pdf_filename(from_dt=from_date, dt_strfmt=dt_strfmt)))

        return self.ReportTuple(
            balance_sheet_statement=bs_report,
            income_statement=is_report,
            cash_flow_statement=cfs_report
        )


class IOMixIn(
    IODatabaseMixIn,
    IOReportMixIn
):
    pass
