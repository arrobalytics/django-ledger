from collections import OrderedDict

from django.core.exceptions import ValidationError
from pandas import DataFrame

from django_ledger.models.accounts import validate_roles
from django_ledger.models.journalentry import validate_activity, JournalEntryModel
from django_ledger.models.transactions import TransactionModel


class LazyImporter:
    """
    This class eliminates the circle dependency between models.
    """
    EM_IMPORTED = None
    LM_IMPORTED = None

    def get_entity_model(self):
        if not self.EM_IMPORTED:
            from django_ledger.models.entity import EntityModel
            self.EM_IMPORTED = EntityModel
        return self.EM_IMPORTED

    def get_ledger_model(self):
        if not self.LM_IMPORTED:
            from django_ledger.models.ledger import LedgerModel
            self.LM_IMPORTED = LedgerModel
        return self.LM_IMPORTED


lazy_importer = LazyImporter()

FIELD_MAP = OrderedDict({'id': 'je_id',
                         'txs__tx_type': 'tx_type',
                         'txs__account__code': 'code',
                         'txs__account__name': 'name',
                         'txs__account__role': 'role',
                         'txs__account__role_bs': 'role_bs',
                         'txs__account__balance_type': 'balance_type',
                         'txs__amount': 'amount'})

DB_FIELDS = [k for k, _ in FIELD_MAP.items()]
VALUES_IDX = [v for _, v in FIELD_MAP.items()]

IDX_CODE = VALUES_IDX.index('code')
IDX_BALANCE = VALUES_IDX.index('amount')
IDX_TX_TYPE = VALUES_IDX.index('tx_type')
IDX_BALANCE_TYPE = VALUES_IDX.index('balance_type')


def process_signs(record):
    """
    Reverse the signs for contra accounts if requested.
    :param record: DF row.
    :return: A Df Row.
    """
    if all([record['role_bs'] == 'assets',
            record['balance_type'] == 'credit']):
        record['balance'] = -record['balance']
    if all([record['role_bs'] in ('liabilities', 'equity', 'other'),
            record['balance_type'] == 'debit']):
        record['balance'] = -record['balance']
    return record


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

        if all([isinstance(self, lazy_importer.get_entity_model()),
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

        if isinstance(self, lazy_importer.get_entity_model()):
            jes = JournalEntryModel.objects.on_entity(entity=self)
        elif isinstance(self, lazy_importer.get_ledger_model()):
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
        jes = jes.values(*DB_FIELDS)
        return jes

    def get_jes(self,
                as_of: str = None,
                as_dataframe: bool = False,
                method: str = 'bs',
                activity: str = None,
                role: str = None,
                account: str = None):

        if method != 'bs':
            role = ['in', 'ex']
        if method == 'ic-op':
            activity = ['op']
        elif method == 'ic-inv':
            activity = ['inv']
        elif method == 'ic-fin':
            activity = ['fin']

        # values
        je_txs = self.get_je_txs(as_of=as_of,
                                 activity=activity,
                                 role=role,
                                 account=account)

        for tx in je_txs:
            if tx['txs__account__balance_type'] != tx['txs__tx_type']:
                tx['txs__amount'] = -tx['txs__amount']

        account_idx = sorted(set([(acc['txs__account__role_bs'],
                                   acc['txs__account__role'],
                                   acc['txs__account__code'],
                                   acc['txs__account__name'],
                                   acc['txs__account__balance_type']) for acc in je_txs]))
        acc_agg = [
            {
                'role_bs': acc[0],
                'role': acc[1],
                'code': acc[2],
                'name': acc[3],
                'balance_type': acc[4],
                'balance': sum([amt for amt in [je['txs__amount']
                                                for je in je_txs if je['txs__account__code'] == acc[2]]]),
            } for acc in account_idx
        ]

        if as_dataframe:
            return DataFrame(acc_agg)
        return acc_agg

    # Financial Statements -----
    def balance_sheet(self, as_of: str = None, signs: bool = False, as_dataframe: bool = False, activity: str = None):

        bs_data = self.get_jes(as_of=as_of,
                               activity=activity,
                               method='bs',
                               as_dataframe=False)

        if signs:
            bs_data = [process_signs(rec) for rec in bs_data]

        if as_dataframe:
            return DataFrame(bs_data)
        return bs_data

    def income_statement(self, signs: bool = False, as_dataframe: bool = False, activity: str = None):
        method = 'ic'
        if isinstance(activity, str):
            method += '-{x1}'.format(x1=activity)

        ic_data = self.get_jes(method=method,
                               as_dataframe=False)

        if signs:
            ic_data = [process_signs(rec) for rec in ic_data]

        if as_dataframe:
            return DataFrame(ic_data)
        return ic_data

    # def income(self, activity: str = None):
    #     inc_df = self.income_statement(signs=True, as_dataframe=True, activity=activity).sum()
    #     return inc_df

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
