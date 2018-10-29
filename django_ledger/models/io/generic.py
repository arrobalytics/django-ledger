from django.apps import apps
from django.core.exceptions import ValidationError


class IOGenericMixIn:
    ACM = apps.get_model('django_ledger.AccountModel', require_ready=False)
    DEFAULT_CASH_ACCOUNT = 1010
    DEFAULT_REVENUE_ACCOUNT = 4020
    DEFAULT_CAPITAL_ACCOUNT = 3010

    def tx_generic(self, amount, start_date, debit_acc, credit_acc, activity, ledger=None, tx_params=None,
                   freq='nr', end_date=None, desc=None, origin=None, parent_je=None):

        # ledger = ledger or getattr(self, 'ledger') or self
        ledger = ledger or self

        if freq != 'nr' and end_date is None:
            raise ValidationError('Must provide end_date for recurring transaction')
        if not origin:
            origin = 'tx_generic'

        start_date, end_date, je_desc = getattr(self, 'preproc_je')(start_date=start_date,
                                                                    end_date=end_date,
                                                                    desc=desc,
                                                                    origin=origin)

        je = ledger.jes.create(desc=je_desc,
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

        debit_acc = self.ACM.objects.get(code__exact=debit_acc)
        credit_acc = self.ACM.objects.get(code__exact=credit_acc)

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

    # PreSet Transactions -----
    def tx_income(self, income, start_date, activity, ledger=None, end_date=None, desc=None, freq='nr',
                  cash_acc=None, revenue_acc=None):

        ledger = ledger or self

        if not cash_acc:
            cash_acc = self.DEFAULT_CASH_ACCOUNT
        if not revenue_acc:
            revenue_acc = self.DEFAULT_REVENUE_ACCOUNT

        origin = 'tx_income'

        self.tx_generic(ledger=ledger, amount=income, start_date=start_date, end_date=end_date, debit_acc=cash_acc,
                        credit_acc=revenue_acc, origin=origin, activity=activity, freq=freq, desc=desc)

    def tx_expense(self, amount, start_date, activity, exp_acc, cash_acc=None, ledger=None, end_date=None, desc=None,
                   freq='nr'):
        ledger = ledger or getattr(self, 'ledger')

        if not cash_acc:
            cash_acc = self.DEFAULT_CASH_ACCOUNT

        origin = 'tx_expense'
        self.tx_generic(ledger=ledger, amount=amount, start_date=start_date, end_date=end_date, debit_acc=exp_acc,
                        credit_acc=cash_acc, origin=origin, activity=activity, freq=freq, desc=desc)

    def tx_capital(self, capital, start_date, end_date=None, desc=None, freq='nr',
                   cash_acc=None, cap_acc=None, ledger=None):

        if not cash_acc:
            cash_acc = self.DEFAULT_CASH_ACCOUNT
        if not cap_acc:
            cap_acc = self.DEFAULT_CAPITAL_ACCOUNT

        ledger = ledger or self

        origin = 'tx_capital'
        activity = 'other'

        self.tx_generic(ledger=ledger, amount=capital, start_date=start_date, end_date=end_date, debit_acc=cash_acc,
                        credit_acc=cap_acc, origin=origin, activity=activity, freq=freq, desc=desc)
