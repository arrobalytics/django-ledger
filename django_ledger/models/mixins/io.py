from collections import OrderedDict

from django.core.exceptions import ValidationError

from django_ledger.models.journalentry import JournalEntryModel
from django_ledger.models.mixins.ratios import generate_ratios
from django_ledger.models.transactions import TransactionModel
from django_ledger.models_abstracts import account_roles as roles
from django_ledger.models_abstracts.accounts import BS_ROLES
from django_ledger.models_abstracts.accounts import validate_roles
from django_ledger.models_abstracts.journal_entry import validate_activity


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
    :param record: A transaction record.
    :return: A modified record.
    """
    if all([record['role_bs'] == 'assets',
            record['balance_type'] == 'credit']):
        record['balance'] = -record['balance']
    if all([record['role_bs'] in ('liabilities', 'equity', 'other'),
            record['balance_type'] == 'debit']):
        record['balance'] = -record['balance']
    return record


def validate_tx_data(tx_data: list):
    credits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'credit')
    debits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'debit')
    if not credits == debits:
        raise ValidationError(f'Invalid tx data. Credits and debits must match. Currently cr: {credits}, db {debits}.')
    return tx_data


class IOMixIn:
    """
    Controls how transactions are recorded into the ledger.
    """

    def create_je(self,
                  je_date: str,
                  je_txs: list,
                  je_activity: str,
                  je_posted: bool = False,
                  je_ledger=None,
                  je_desc=None,
                  je_origin=None,
                  je_parent=None):

        # Validates that credits/debits balance.
        je_txs = validate_tx_data(je_txs)

        # Validates that the activity is valid.
        je_activity = validate_activity(je_activity)

        if all([isinstance(self, lazy_importer.get_entity_model()),
                not je_ledger]):
            raise ValidationError('Must pass an instance of LedgerModel')

        if not je_ledger:
            je_ledger = self

        txs_accounts = [acc['code'] for acc in je_txs]

        if isinstance(self, lazy_importer.get_entity_model()):
            account_models = self.coa.accounts.all()
        elif isinstance(self, lazy_importer.get_ledger_model()):
            account_models = self.entity.coa.accounts.all()
        else:
            account_models = self.coa.accounts.none()

        avail_accounts = account_models.filter(code__in=txs_accounts)

        je = JournalEntryModel.objects.create(
            ledger=je_ledger,
            description=je_desc,
            date=je_date,
            origin=je_origin,
            activity=je_activity,
            posted=je_posted,
            parent=je_parent)

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
                   accounts: str = None) -> list:

        """
        If account is present all other parameters will be ignored.

        :param as_dataframe:
        :param activity:
        :param role:
        :param accounts:
        :return:
        """

        activity = validate_activity(activity)
        role = validate_roles(role)

        # Checks if self is EntityModel or LedgerModel.
        # Filters queryset to posted Journal Entries only.
        if isinstance(self, lazy_importer.get_entity_model()):
            # Is entity model....
            jes_queryset = JournalEntryModel.on_coa.on_entity_posted(entity=self)
        elif isinstance(self, lazy_importer.get_ledger_model()):
            # Is ledger model ...
            jes_queryset = JournalEntryModel.on_coa.on_ledger_posted(ledger=self)
        else:
            jes_queryset = JournalEntryModel.on_coa.none()

        if as_of:
            jes_queryset = jes_queryset.filter(date__lte=as_of)

        if accounts:
            if isinstance(accounts, str):
                accounts = [accounts]
            jes_queryset = self.journal_entries.filter(txs__account__code__in=accounts)
        if activity:
            if isinstance(activity, str):
                activity = [activity]
            jes_queryset = jes_queryset.filter(activity__in=activity)
        if role:
            if isinstance(role, str):
                role = [role]
            jes_queryset = jes_queryset.filter(txs__account__role__in=role)
        jes_queryset = jes_queryset.values(*DB_FIELDS)
        return jes_queryset

    def get_jes(self,
                as_of: str = None,
                method: str = 'bs',
                activity: str = None,
                role: str = None,
                accounts: str = None):

        if method != 'bs':
            role = roles.ROLES_EARNINGS
        if method == 'ic-op':
            activity = ['op']
        elif method == 'ic-inv':
            activity = ['inv']
        elif method == 'ic-fin':
            activity = ['fin']

        je_txs = self.get_je_txs(as_of=as_of,
                                 activity=activity,
                                 role=role,
                                 accounts=accounts)

        # reverts the amount sign if the tx_type does not math the account_type.
        for tx in je_txs:
            if tx['txs__account__balance_type'] != tx['txs__tx_type']:
                tx['txs__amount'] = -tx['txs__amount']

        account_idx = sorted(set([(
            BS_ROLES.get(acc['txs__account__role']),
            acc['txs__account__role'],
            acc['txs__account__code'],
            acc['txs__account__name'],
            acc['txs__account__balance_type']
        ) for acc in je_txs if acc['txs__amount']]))

        tx_aggregate = [
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

        return tx_aggregate

    # Financial Statements -----
    # todo: rename this method to something more generic.
    def balance_sheet(self, as_of: str = None, signs: bool = False, activity: str = None):

        bs_data = self.get_jes(as_of=as_of,
                               activity=activity,
                               method='bs')

        # process signs will return negative balances for contra-accounts...
        if signs:
            bs_data = [process_signs(rec) for rec in bs_data]
        return bs_data

    def income_statement(self, signs: bool = False, activity: str = None):
        method = 'ic'
        if isinstance(activity, str):
            method += '-{x1}'.format(x1=activity)

        ic_data = self.get_jes(method=method)

        if signs:
            ic_data = [process_signs(rec) for rec in ic_data]

        return ic_data

    def digest(self,
               activity: str = None,
               as_of: str = None,
               ratios: bool = False) -> dict:
        tx_data = self.balance_sheet(signs=True, activity=activity, as_of=as_of)

        assets = [acc for acc in tx_data if acc['role_bs'] == 'assets']
        cash = [acc for acc in assets if acc['role'] in roles.ROLE_CA_CASH]
        # current_assets = [acc['balance'] for acc in bs_data if acc['role'] in roles.ROLES_CURRENT_ASSETS]
        liabilities = [acc for acc in tx_data if acc['role_bs'] == 'liabilities']
        # current_liabilities = [acc['balance'] for acc in bs_data if acc['role'] in roles.ROLES_CURRENT_LIABILITIES]
        equity = [acc for acc in tx_data if acc['role_bs'] == 'equity']
        capital = [acc for acc in equity if acc['role'] in roles.ROLES_CAPITAL]
        earnings = [acc for acc in equity if acc['role'] in roles.ROLES_EARNINGS]

        total_assets = sum([acc['balance'] for acc in assets])
        total_cash = sum([acc['balance'] for acc in cash])
        # total_current_assets = sum(current_assets)
        total_liabilities = sum([acc['balance'] for acc in liabilities])
        # total_current_liabilities = sum(current_liabilities)
        total_capital = sum([acc['balance'] for acc in capital])
        total_income = sum([acc['balance'] for acc in earnings if acc['role'] in roles.ROLES_INCOME])
        total_expenses = -sum([acc['balance'] for acc in earnings if acc['role'] in roles.ROLES_EXPENSES])

        retained_earnings = sum([acc['balance'] for acc in earnings])

        total_equity = total_capital + retained_earnings - total_liabilities
        total_liabilities_equity = total_liabilities + total_capital + retained_earnings

        digest_data = {
            'bs_data': tx_data,
            'assets': assets,
            'total_assets': total_assets,
            'total_cash': total_cash,
            'liabilities': liabilities,
            'total_liabilities': total_liabilities,
            'equity': equity,
            'total_equity': total_equity,
            'capital': capital,
            'total_capital': total_capital,
            'earnings': earnings,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'retained_earnings': retained_earnings,
            'total_liabilities_equity': total_liabilities_equity,
        }

        if ratios:
            digest_data['ratios'] = dict()
            digest_data = generate_ratios(digest=digest_data,
                                          tx_data=tx_data)

        return digest_data
