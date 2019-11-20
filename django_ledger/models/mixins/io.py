from django.core.exceptions import ValidationError

from django_ledger.models.journalentry import validate_activity, JournalEntryModel
from django_ledger.models.transactions import TransactionModel


def validate_tx_data(tx_data: dict) -> dict:
    credits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'credit')
    debits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'debit')
    if not credits == debits:
        raise ValidationError(f'Invalid tx data. Credits and debits must match. Currently cr: {credits}, db {debits}.')


class IOMixIn:
    """
    Controls how transactions are recorded into the ledger.
    Contains functions to programmatically get accounts for Journal Entries.
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
        if not je_ledger:
            je_ledger = self

        tx_axcounts = [acc['code'] for acc in je_txs]
        account_models = getattr(self, 'get_accounts')
        avail_accounts = account_models(status='available').filter(code__in=tx_axcounts)
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
        TransactionModel.objects.bulk_create(txs_list)

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
