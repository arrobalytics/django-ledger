from django.core.exceptions import ValidationError

from django_ledger.models.journalentry import validate_activity, validate_freq, JournalEntryModel
from django_ledger.models.transactions import TransactionModel


def validate_tx_data(tx_data: dict) -> dict:
    credits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'credit')
    debits = sum(tx['amount'] for tx in tx_data if tx['tx_type'] == 'debit')
    if not credits == debits:
        raise ValidationError(f'Invalid tx data. Credits and debits must match. Currently cr: {credits}, db {debits}.')


class IOGenericMixIn:
    """
    Controls how transactions are recorded into the ledger.
    Contains functions to programmatically get accounts for Journal Entries.
    """

    DEFAULT_ASSET_ACCOUNT = 1010
    DEFAULT_LIABILITY_ACCOUNT = None
    DEFAULT_CAPITAL_ACCOUNT = 3010

    DEFAULT_INCOME_ACCOUNT = 4020
    DEFAULT_EXPENSE_ACCOUNT = None

    def tx_generic(self,
                   amount: float,
                   start_date,
                   debit_acc,
                   credit_acc,
                   activity: str,
                   ledger=None,
                   tx_params=None,
                   freq='nr',
                   end_date=None,
                   desc=None,
                   origin=None,
                   parent_je=None):

        activity = validate_activity(activity)
        freq = validate_freq(freq)
        ledger = ledger or self

        if all([freq != 'nr',
                not end_date]):
            raise ValidationError('Must provide end_date for recurring transaction')

        if not origin:
            origin = 'tx_generic'

        preproc_je = getattr(self, 'preproc_je')
        start_date, end_date, je_desc = preproc_je(start_date=start_date,
                                                   end_date=end_date,
                                                   desc=desc,
                                                   ledger=ledger,
                                                   origin=origin)

        je = ledger.journal_entry.create(desc=je_desc,
                                         freq=freq,
                                         start_date=start_date,
                                         end_date=end_date,
                                         origin=origin,
                                         activity=activity,
                                         parent=parent_je)

        gen_params = dict()
        gen_params['amount'] = amount
        gen_params['freq'] = freq

        if tx_params and isinstance(tx_params, dict):
            gen_params.update(tx_params)

        get_accounts = getattr(self, 'get_accounts')
        avail_accounts = get_accounts(status='available')
        debit_acc = avail_accounts.get(account__code__iexact=debit_acc).account
        credit_acc = avail_accounts.get(account__code__iexact=credit_acc).account

        # todo: can both create be done at once?
        je.txs.create(tx_type='debit',
                      account=debit_acc,
                      params=gen_params,
                      amount=amount)

        je.txs.create(tx_type='credit',
                      account=credit_acc,
                      params=gen_params,
                      amount=amount)

        try:
            # todo: maybe can pass je to clean() if error???...
            je.clean()
        except ValidationError:
            je.transactions.all().delete()
            je.delete()
            raise ValidationError('Something went wrong cleaning journal entry ID:{x1}'.format(x1=je.id))

    def tx_optimized(self,
                     je_date: str,
                     je_txs: dict,
                     je_activity: str,
                     je_ledger=None,
                     je_desc=None,
                     je_origin=None,
                     je_parent=None):

        freq = 'nr'
        validate_tx_data(je_txs)

        # todo: make this a function without a return.
        je_activity = validate_activity(je_activity)
        if not je_ledger:
            je_ledger = self

        if not je_origin:
            je_origin = 'tx_optimized'

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
