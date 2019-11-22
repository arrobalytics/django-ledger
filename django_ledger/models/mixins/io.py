import calendar
from collections import OrderedDict, namedtuple
from datetime import datetime

import pandas as pd
from django.core.exceptions import ValidationError

from django_ledger.models.accounts import validate_roles
from django_ledger.models.coa import get_acc_idx
from django_ledger.models.journalentry import validate_activity, JournalEntryModel
from django_ledger.models.transactions import TransactionModel


def get_entity_model():
    from django_ledger.models.entity import EntityModel
    return EntityModel


def get_ledger_model():
    from django_ledger.models.ledger import LedgerModel
    return LedgerModel


FIELD_MAP = OrderedDict({'id': 'je_id',
                         'origin': 'origin',
                         'date': 'date',
                         'activity': 'activity',
                         'txs__id': 'tx_id',
                         'txs__tx_type': 'tx_type',
                         'txs__account': 'account',
                         'txs__account__code': 'code',
                         'txs__account__name': 'name',
                         'txs__account__balance_type': 'balance_type',
                         'txs__account__role': 'role',
                         'txs__amount': 'amount'})

DB_FIELDS = [k for k, _ in FIELD_MAP.items()]
NEW_FIELDS = [v for _, v in FIELD_MAP.items()]
NEW_FIELDS.append('je_date')
DATE_INDEX = NEW_FIELDS.index('date')


def get_je_records(queryset):
    jes_records = queryset.values_list(*DB_FIELDS)
    jes_list = list()
    # todo: this can be done from the database using extract.
    for jer in jes_records:
        date = jer[DATE_INDEX]
        je_date = datetime(year=date.year,
                           month=date.month,
                           day=calendar.monthrange(date.year, date.month)[-1])
        jer = jer + (je_date,)
        jes_list.append(jer)
    je_tuple = namedtuple('JERecord', ', '.join(NEW_FIELDS))
    jes_records = [je_tuple(*je) for je in jes_list]
    return jes_records


def process_signs(row):
    """
    Reverse the signs for contra accounts if requested.
    :param row: DF row.
    :return: A Df Row.
    """
    idx = [x.lower() for x in row.name]
    if all(['assets' in idx,
            'credit' in idx]):
        row = -row
    if all([any(['liabilities' in idx,
                 'equity' in idx,
                 'other' in idx]),
            'debit' in idx]):
        row = -row
    return row


def tx_type_digest(je):
    """
    Interprets the transaction type against the account balance type and adds/subtracts accordingly.
    :param je: Joutnal entry named tuple.
    :return: JE namedtuple.
    """
    if je['tx_type'] == je['balance_type']:
        je['amount'] = pd.to_numeric(je['amount'])
    else:
        je['amount'] = -pd.to_numeric(je['amount'])
    return je


def validate_tx_data(tx_data: dict) -> dict:
    credits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'credit')
    debits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'debit')
    if not credits == debits:
        raise ValidationError(f'Invalid tx data. Credits and debits must match. Currently cr: {credits}, db {debits}.')


class IOMixIn:
    """
    Controls how transactions are recorded into the ledger.
    """

    DEFAULT_ASSET_ACCOUNT = 1010
    DEFAULT_LIABILITY_ACCOUNT = None
    DEFAULT_CAPITAL_ACCOUNT = 3010

    DEFAULT_INCOME_ACCOUNT = 4020
    DEFAULT_EXPENSE_ACCOUNT = None

    def create_je(self,
                  je_date: str,
                  je_txs: dict,
                  je_activity: str,
                  je_ledger=None,
                  je_desc=None,
                  je_origin=None,
                  je_parent=None):

        validate_tx_data(je_txs)

        # todo: make this a function without a return.
        je_activity = validate_activity(je_activity)

        if all([isinstance(self, get_entity_model()),
                not je_ledger]):
            raise ValidationError('Must pass an instance of LedgerModel')

        if not je_ledger:
            je_ledger = self

        tx_axcounts = [acc['code'] for acc in je_txs]
        account_models = getattr(self, 'get_accounts')
        avail_accounts = account_models().filter(code__in=tx_axcounts)

        je = JournalEntryModel.objects.create(
            ledger=je_ledger,
            description=je_desc,
            date=je_date,
            origin=je_origin,
            activity=je_activity,
            parent=je_parent
        )
        txs_list = [
            TransactionModel(
                account=avail_accounts.get(code__iexact=tx['code']),
                tx_type=tx['tx_type'],
                amount=tx['amount'],
                description=tx['description'],
                journal_entry=je
            ) for tx in je_txs
        ]
        txs = TransactionModel.objects.bulk_create(txs_list)
        return txs

    def get_je_txs(self,
                   as_of: str = None,
                   activity: str = None,
                   role: str = None,
                   account: str = None) -> list:

        """
        If account is present all other parameters will be ignored.

        :param as_dataframe:
        :param activity:
        :param role:
        :param account:
        :return:
        """

        activity = validate_activity(activity)
        role = validate_roles(role)

        if isinstance(self, get_entity_model()):
            jes = JournalEntryModel.objects.on_entity(entity=self)
        elif isinstance(self, get_ledger_model()):
            jes = self.journal_entry.filter(ledger__exact=self)

        if as_of:
            jes = jes.filter(date__lte=as_of)

        if account:
            if isinstance(account, str) or isinstance(account, int):
                account = [account]
            jes = self.journal_entry.filter(txs__account__code__in=account)
        if activity:
            if isinstance(activity, str):
                activity = [activity]
            jes = jes.filter(activity__in=activity)
        if role:
            if isinstance(role, str):
                role = [role]
            jes = jes.filter(txs__account__role__in=role)

        jes_records = get_je_records(queryset=jes)
        return jes_records

    def get_jes(self, as_of: str = None, as_dataframe: bool = False, method: str = 'bs', activity: str = None,
                role: str = None, account: str = None):

        if method != 'bs':
            role = ['in', 'ex']
        if method == 'ic-op':
            activity = ['op']
        elif method == 'ic-inv':
            activity = ['inv']
        elif method == 'ic-fin':
            activity = ['fin']

        je_txs = self.get_je_txs(as_of=as_of,
                                 activity=activity,
                                 role=role,
                                 account=account)

        df = pd.DataFrame([(je.code,
                            je.amount,
                            je.tx_type,
                            je.balance_type) for je in je_txs],
                          columns=['code', 'amount', 'tx_type', 'balance_type'])
        df = df.apply(tx_type_digest,
                      axis=1).loc[:, ['code', 'amount']].set_index('code')
        df = df.groupby('code').sum()
        df.rename(columns={
            'amount': 'balance'
        }, inplace=True)
        df = pd.merge(
            left=get_acc_idx(coa_model=self.get_coa(),
                             as_dataframe=True),
            right=df,
            how='inner',
            left_index=True,
            right_index=True)

        if as_dataframe:
            return df
        return df.reset_index().to_dict(orient='records')

    # Financial Statements -----
    def balance_sheet(self, as_of: str = None, signs: bool = False, as_dataframe: bool = False, activity: str = None):

        bs_df = self.get_jes(as_of=as_of,
                             activity=activity,
                             method='bs',
                             as_dataframe=True)

        if signs:
            bs_df = bs_df.apply(process_signs, axis=1)

        if not as_dataframe:
            return bs_df.reset_index().to_dict(orient='records')
        return bs_df

    def income_statement(self, signs: bool = False, as_dataframe: bool = False, activity: str = None):
        method = 'ic'
        if isinstance(activity, str):
            method += '-{x1}'.format(x1=activity)

        ic_df = self.get_jes(method=method,
                             as_dataframe=True)

        if signs:
            ic_df = ic_df.apply(process_signs, axis=1)

        if not as_dataframe:
            return ic_df.reset_index().to_dict(orient='records')
        return ic_df

    def income(self, activity: str = None):
        inc_df = self.income_statement(signs=True, as_dataframe=True, activity=activity).sum()
        return inc_df

    def get_asset_account(self):
        """
        This function programmatically returns the asset account to be used on a journal entry.
        :return: Account code as a string in order to match field data type.
        """
        return str(self.DEFAULT_ASSET_ACCOUNT)

    def get_liability_account(self):
        """
        This function programmatically returns the liability account to be used on a journal entry.
        :return: Account code as a string in order to match field data type.
        """
        return self.DEFAULT_LIABILITY_ACCOUNT

    def get_capital_account(self):
        """
        This function programmatically returns the capital account to be used on a journal entry.
        :return: Account code as a string in order to match field data type.
        """
        return self.DEFAULT_CAPITAL_ACCOUNT

    def get_income_account(self):
        """
        This function programmatically returns the income account to be used on a journal entry.
        :return: Account code as a string in order to match field data type.
        """
        return self.DEFAULT_EXPENSE_ACCOUNT

    def get_expense_account(self):
        """
        This function programmatically returns the expense account to be used on a journal entry.
        :return: Account code as a string in order to match field data type.
        """
        return self.DEFAULT_EXPENSE_ACCOUNT
