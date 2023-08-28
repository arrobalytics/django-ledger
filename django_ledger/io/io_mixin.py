"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from collections import defaultdict, namedtuple
from datetime import datetime, date, timedelta
from itertools import groupby
from pathlib import Path
from random import choice
from typing import List, Set, Union, Tuple, Optional, Dict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum, QuerySet
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import make_aware, is_naive, localtime

from django_ledger.exceptions import InvalidDateInputError, TransactionNotInBalanceError
from django_ledger.io import roles as roles_module
from django_ledger.io.io_context import (RoleContextManager, GroupContextManager, ActivityContextManager,
                                         BalanceSheetStatementContextManager, IncomeStatementContextManager,
                                         CashFlowStatementContextManager)
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


def balance_tx_data(tx_data: list, perform_correction: bool = True) -> bool:
    if tx_data:

        IS_TX_MODEL, is_valid, diff = diff_tx_data(tx_data, raise_exception=perform_correction)

        if not perform_correction and abs(diff) > settings.DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE:
            return False

        while not is_valid:

            tx_type_choice = choice(['debit', 'credit'])
            txs_candidates = list(tx for tx in tx_data if tx.tx_type == tx_type_choice)
            if len(txs_candidates) > 0:
                tx = choice(list(tx for tx in tx_data if tx.tx_type == tx_type_choice))

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


def validate_io_date(dt: Union[str, date, datetime], no_parse_localdate: bool = True) -> Optional[datetime]:
    if not dt:
        return

    if isinstance(dt, date):
        dt = make_aware(
            value=datetime.combine(
                dt,
                datetime.min.time()
            ))
        return dt
    elif isinstance(dt, datetime):
        if is_naive(dt):
            return make_aware(dt)
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


class IODatabaseMixIn:
    """
    Controls how transactions are recorded into the ledger.
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

    # def is_time_bounded(self, from_date, to_date):

    def database_digest(self,
                        txs_queryset: QuerySet,
                        entity_slug: str = None,
                        unit_slug: str = None,
                        user_model: UserModel = None,
                        from_date: date = None,
                        to_date: date = None,
                        activity: str = None,
                        role: str = None,
                        accounts: str or List[str] or Set[str] = None,
                        posted: bool = True,
                        exclude_zero_bal: bool = True,
                        by_activity: bool = False,
                        by_tx_type: bool = False,
                        by_period: bool = False,
                        by_unit: bool = False):

        closing_entry_list = None
        if settings.DJANGO_LEDGER_USE_CLOSING_ENTRIES:
            if not from_date:
                entity_model = self.get_entity_model_from_io()
                closing_entry_date = entity_model.select_closing_entry_for_io_date(to_date=to_date)

                if closing_entry_date:
                    # closing_entry_list = entity_model.get_closing_entry_cache_for_date(
                    #     closing_date=closing_entry_date,
                    #     force_cache_update=True
                    # )
                    from_date_d = closing_entry_date + timedelta(days=1)
                    print('Orig From:', from_date)
                    print('New from:', from_date_d)
                    print('To Date:', to_date)
                    print(closing_entry_list)

        if not txs_queryset:
            TransactionModel = lazy_loader.get_txs_model()

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

        if exclude_zero_bal:
            txs_queryset = txs_queryset.filter(amount__gt=0)

        if posted:
            txs_queryset = txs_queryset.posted()

        if from_date:
            txs_queryset = txs_queryset.from_date(from_date=from_date)

        if to_date:
            txs_queryset = txs_queryset.to_date(to_date=to_date)

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

        return closing_entry_list, txs_queryset.values(*VALUES).annotate(**ANNOTATE).order_by(*ORDER_BY)

    def python_digest(self,
                      txs_queryset: Optional[QuerySet] = None,
                      user_model: Optional[UserModel] = None,
                      to_date: date = None,
                      from_date: date = None,
                      equity_only: bool = False,
                      activity: str = None,
                      entity_slug: str = None,
                      unit_slug: str = None,
                      role: Optional[Union[Set[str], List[str]]] = None,
                      accounts: Optional[Union[Set[str], List[str]]] = None,
                      signs: bool = False,
                      by_unit: bool = False,
                      by_activity: bool = False,
                      by_tx_type: bool = False,
                      by_period: bool = False) -> list or tuple:

        if equity_only:
            role = roles_module.GROUP_EARNINGS

        closing_entry_list, txs_queryset = self.database_digest(
            user_model=user_model,
            txs_queryset=txs_queryset,
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

        for tx_model in txs_queryset:
            if tx_model['account__balance_type'] != tx_model['tx_type']:
                tx_model['balance'] = -tx_model['balance']

        # txs_list = list(txs_queryset)
        # txs_list.sort(key=lambda a: (
        #     a['account__uuid'],
        #     str(a.get('journal_entry__entity_unit__uuid', '')) if by_unit else '',
        #     a['dt_idx'].year if by_period else 0,
        #     a['dt_idx'].month if by_period else 0,
        #     str(a['journal_entry__activity']) if by_activity else None,
        #     a['tx_type'] if by_tx_type else '',
        # ))

        accounts_gb_code = groupby(txs_queryset,
                                   key=lambda a: (
                                       a['account__uuid'],
                                       a.get('journal_entry__entity_unit__uuid') if by_unit else None,
                                       a.get('dt_idx').year if by_period else None,
                                       a.get('dt_idx').month if by_period else None,
                                       a.get('journal_entry__activity') if by_activity else None,
                                       a.get('tx_type') if by_tx_type else None,
                                   ))

        gb_digest = [self.aggregate_balances(k, g) for k, g in accounts_gb_code]

        for acc in gb_digest:
            acc['balance_abs'] = abs(acc['balance'])

        if signs:
            TransactionModel = lazy_loader.get_txs_model()
            for acc in gb_digest:
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

        return txs_queryset, gb_digest

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
               entity_slug: str = None,
               unit_slug: str = None,
               user_model: UserModel = None,
               txs_queryset: QuerySet = None,
               as_io_digest: bool = False,
               accounts: Optional[Union[Set[str], List[str]]] = None,
               role: Optional[Union[Set[str], List[str]]] = None,
               activity: str = None,
               signs: bool = True,
               to_date: Union[str, datetime, date] = None,
               from_date: Union[str, datetime, date] = None,
               process_roles: bool = False,
               process_groups: bool = False,
               process_ratios: bool = False,
               process_activity: bool = False,
               equity_only: bool = False,
               by_period: bool = False,
               by_unit: bool = False,
               by_activity: bool = False,
               by_tx_type: bool = False,
               digest_name: str = None,
               balance_sheet_statement: bool = False,
               income_statement: bool = False,
               cash_flow_statement: bool = False,
               ) -> Union[Tuple, IODigestContextManager]:

        if balance_sheet_statement:
            from_date = None

        if cash_flow_statement:
            by_activity = True

        if activity:
            activity = validate_activity(activity)
        if role:
            role = roles_module.validate_roles(role)

        from_date, to_date = validate_dates(from_date, to_date)

        io_data = defaultdict(lambda: dict())
        io_data['io_model'] = self
        io_data['from_date'] = from_date
        io_data['to_date'] = to_date
        io_data['by_unit'] = by_unit
        io_data['by_period'] = by_period
        io_data['by_activity'] = by_activity
        io_data['by_tx_type'] = by_tx_type

        txs_qs, accounts_digest = self.python_digest(
            txs_queryset=txs_queryset,
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
            by_tx_type=by_tx_type
        )

        io_data['txs_qs'] = txs_qs
        io_data['accounts'] = accounts_digest

        if process_roles:
            roles_mgr = RoleContextManager(
                io_data=io_data,
                by_period=by_period,
                by_unit=by_unit
            )

            # idea: change digest() name to something else? maybe aggregate, calculate?...
            io_data = roles_mgr.digest()

        if any([
            process_groups,
            balance_sheet_statement,
            income_statement,
            cash_flow_statement
        ]):
            group_mgr = GroupContextManager(
                io_data=io_data,
                by_period=by_period,
                by_unit=by_unit
            )
            io_data = group_mgr.digest()

            # todo: migrate this to group manager...
            io_data['group_account']['GROUP_ASSETS'].sort(
                key=lambda acc: roles_module.ROLES_ORDER_ASSETS.index(acc['role']))
            io_data['group_account']['GROUP_LIABILITIES'].sort(
                key=lambda acc: roles_module.ROLES_ORDER_LIABILITIES.index(acc['role']))
            io_data['group_account']['GROUP_CAPITAL'].sort(
                key=lambda acc: roles_module.ROLES_ORDER_CAPITAL.index(acc['role']))

        if process_ratios:
            ratio_gen = FinancialRatioManager(io_data=io_data)
            io_data = ratio_gen.digest()

        if process_activity:
            activity_manager = ActivityContextManager(io_data=io_data, by_unit=by_unit, by_period=by_period)
            activity_manager.digest()

        if balance_sheet_statement:
            balance_sheet_mgr = BalanceSheetStatementContextManager(io_data=io_data)
            io_data = balance_sheet_mgr.digest()

        if income_statement:
            income_statement_mgr = IncomeStatementContextManager(io_data=io_data)
            io_data = income_statement_mgr.digest()

        if cash_flow_statement:
            cfs = CashFlowStatementContextManager(io_data=io_data)
            io_data = cfs.digest()

        if as_io_digest:
            return IODigestContextManager(io_data=io_data)

        if not digest_name:
            digest_name = 'tx_digest'

        digest_results = {
            digest_name: io_data
        }

        return txs_qs, digest_results

    def commit_txs(self,
                   je_timestamp: Union[str, datetime, date],
                   je_txs: List[Dict],
                   je_posted: bool = False,
                   je_ledger_model=None,
                   je_desc=None,
                   je_origin=None):
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

        # if isinstance(self, lazy_loader.get_entity_model()):

        # Validates that credits/debits balance.
        balance_tx_data(je_txs)

        if all([
            isinstance(self, lazy_loader.get_entity_model()),
            not je_ledger_model
        ]):
            raise ValidationError('Must pass an instance of LedgerModel')

        if not je_ledger_model:
            je_ledger_model = self

        JournalEntryModel = lazy_loader.get_journal_entry_model()

        je_timestamp = validate_io_date(dt=je_timestamp)

        je_model = JournalEntryModel(
            ledger=je_ledger_model,
            description=je_desc,
            timestamp=je_timestamp,
            origin=je_origin,
        )

        # verify is False, no transactions are present yet....
        je_model.save(verify=False)

        TransactionModel = lazy_loader.get_txs_model()
        txs_models = [
            TransactionModel(
                **txm_kwargs,
                journal_entry=je_model,
                stagedtransactionmodel=txm_kwargs.get('staged_tx_model')
            ) for txm_kwargs in je_txs
        ]
        txs_models = TransactionModel.objects.bulk_create(txs_models)

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
            bs_report.output(base_dir.joinpath(bs_report.get_pdf_filename()))

            is_report.create_pdf_report()
            is_report.output(base_dir.joinpath(is_report.get_pdf_filename()))

            cfs_report.create_pdf_report()
            cfs_report.output(base_dir.joinpath(cfs_report.get_pdf_filename()))

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
