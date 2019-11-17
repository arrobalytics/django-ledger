from django.core.exceptions import ValidationError

from django_ledger.models.journalentry import validate_activity, validate_freq


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

    # # PreSet Transactions -----
    # def tx_income(self, income, start_date, activity, ledger=None, end_date=None, desc=None, freq='nr',
    #               cash_acc=None, revenue_acc=None):
    #
    #     ledger = ledger or self
    #
    #     if not cash_acc:
    #         cash_acc = self.DEFAULT_CASH_ACCOUNT
    #     if not revenue_acc:
    #         revenue_acc = self.DEFAULT_REVENUE_ACCOUNT
    #
    #     origin = 'tx_income'
    #
    #     self.tx_generic(ledger=ledger, amount=income, start_date=start_date, end_date=end_date, debit_acc=cash_acc,
    #                     credit_acc=revenue_acc, origin=origin, activity=activity, freq=freq, desc=desc)
    #
    # def tx_expense(self, amount, start_date, activity, exp_acc, cash_acc=None, ledger=None, end_date=None, desc=None,
    #                freq='nr'):
    #     ledger = ledger or getattr(self, 'ledger')
    #
    #     if not cash_acc:
    #         cash_acc = self.DEFAULT_CASH_ACCOUNT
    #
    #     origin = 'tx_expense'
    #     self.tx_generic(ledger=ledger, amount=amount, start_date=start_date, end_date=end_date, debit_acc=exp_acc,
    #                     credit_acc=cash_acc, origin=origin, activity=activity, freq=freq, desc=desc)
    #
    # def tx_capital(self, capital, start_date, end_date=None, desc=None, freq='nr',
    #                cash_acc=None, cap_acc=None, ledger=None):
    #
    #     if not cash_acc:
    #         cash_acc = self.DEFAULT_CASH_ACCOUNT
    #     if not cap_acc:
    #         cap_acc = self.DEFAULT_CAPITAL_ACCOUNT
    #
    #     ledger = ledger or self
    #
    #     origin = 'tx_capital'
    #     activity = 'other'
    #
    #     self.tx_generic(ledger=ledger, amount=capital, start_date=start_date, end_date=end_date, debit_acc=cash_acc,
    #                     credit_acc=cap_acc, origin=origin, activity=activity, freq=freq, desc=desc)
