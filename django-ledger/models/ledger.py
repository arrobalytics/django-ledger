import pandas as pd
from django.core.validators import MinValueValidator
from django.db import models
from django_pandas.io import read_frame
from pandas.tseries.offsets import MonthEnd

from .io.generic import IOGenericMixIn
from .io.preproc import IOPreProcMixIn
from .transactions import TransactionModel
from .utils import get_acc_idx


class LedgerModel(models.Model,
                  IOPreProcMixIn,
                  IOGenericMixIn):

    SCOPES = (
        ('a', 'Actual'),
        ('f', 'Forecast'),
        ('b', 'Baseline')
    )

    name = models.CharField(max_length=50)
    scope = models.CharField(max_length=1, choices=SCOPES)
    entity = models.ForeignKey('books.EntityModel',
                               on_delete=models.CASCADE)

    years_horizon = models.IntegerField(default=10, validators=[MinValueValidator(0)])

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Ledger'

    def __str__(self):
        return '{scope}: {id}'.format(scope=self.get_scope_display(),
                                      id=self.pk)

    def get_jes_df(self):
        jes = self.jes.all()
        jes_df = read_frame(jes, verbose=False)
        jes_df.rename(columns={'id': 'je_id'}, inplace=True)
        jes_df.set_index('je_id', inplace=True)
        jes_df['start_date'] = pd.to_datetime(jes_df['start_date'])
        jes_df['end_date'] = pd.to_datetime(jes_df['end_date'])
        return jes_df

    def get_tx_df(self):
        # todo: Do we need to hit DB twice to get TXs if we got JEs???
        tx = TransactionModel.objects.filter(journal_entry__ledger__exact=self)
        tx_df = read_frame(tx, verbose=False)
        tx_df.rename(columns={'id': 'tx_id'}, inplace=True)
        tx_df.set_index('tx_id', inplace=True)
        return tx_df

    def get_jes_tx_df(self, to_json=False, activity=None, role=None, account=None):

        """
        If account is present all other parameters will be ignored.

        :param to_json:
        :param activity:
        :param role:
        :param account:
        :return:
        """
        # fixme: add criteria for acc & other params.
        if account is None:
            if isinstance(activity, str):
                activity = [activity]
            if isinstance(role, str):
                role = [role]

            if activity is None and role is None:
                jes = self.jes.filter(ledger__exact=self)
            elif activity is not None and role is None:
                jes = self.jes.filter(ledger__exact=self, activity__in=activity)
            elif activity is None and role is not None:
                jes = self.jes.filter(ledger__exact=self, txs__account__role__in=role)
            elif activity is not None and role is not None:
                jes = self.jes.filter(ledger__exact=self, activity__in=activity,
                                      txs__account__role__in=role)
            else:
                jes = self.jes.filter(forecast__exact=self)

        else:
            if isinstance(account, str) or isinstance(account, int):
                account = [account]

            if activity is None and role is None:
                jes = self.jes.filter(ledger__exact=self,
                                      txs__account__code__in=account)
            elif activity is not None and role is None:
                jes = self.jes.filter(ledger__exact=self,
                                      activity__in=activity,
                                      txs__account__code__in=account)
            elif activity is None and role is not None:
                jes = self.jes.filter(ledger__exact=self,
                                      txs__account__acc_role__in=role,
                                      txs__account__code__in=account)
            elif activity is not None and role is not None:
                jes = self.jes.filter(ledger__exact=self,
                                      activity__in=activity,
                                      txs__account__role__in=role,
                                      txs__account__code__in=account)
            else:
                jes = self.jes.filter(ledger__exact=self,
                                      txs__account__code__in=account)

        jes_tx_df = read_frame(jes, fieldnames=['id', 'origin', 'freq', 'start_date', 'end_date', 'activity',
                                                'txs__id', 'txs__tx_type',
                                                'txs__account__code',
                                                'txs__account__name',
                                                'txs__account__balance_type',
                                                'txs__account__role',
                                                'txs__amount', 'txs__params'],
                               verbose=False)

        jes_tx_df.rename(columns={'id': 'je_id',
                                  'txs__id': 'tx_id',
                                  'txs__tx_type': 'tx_type',
                                  'txs__account': 'account',
                                  'txs__account__code': 'code',
                                  'txs__account__name': 'name',
                                  'txs__account__balance_type': 'balance_type',
                                  'txs__account__role': 'role',
                                  'txs__amount': 'amount',
                                  'txs__params': 'params'},
                         inplace=True)

        jes_tx_df.set_index(keys=['je_id', 'tx_id'], inplace=True)
        jes_tx_df['start_date'] = pd.to_datetime(jes_tx_df['start_date'])
        jes_tx_df['end_date'] = pd.to_datetime(jes_tx_df['end_date'])

        pe_start = pd.to_datetime(jes_tx_df['start_date'], format="%Y%m") + MonthEnd(0)
        jes_tx_df['pe_start'] = pe_start

        pe_finish = pd.to_datetime(jes_tx_df['end_date'], format="%Y%m") + MonthEnd(0)
        jes_tx_df['pe_finish'] = pe_finish

        def sm_pe(row):
            if row['freq'][0] == 's':
                row['pe_finish'] = row['pe_finish'] - pd.DateOffset(months=1) + MonthEnd(0)
            return row

        jes_tx_df = jes_tx_df.apply(func=sm_pe, axis=1)

        if to_json is True:
            return jes_tx_df.to_json()
        else:
            return jes_tx_df

    def get_ts_df(self, cum=True, to_json=False, method='bs', activity=None, role=None, account=None):

        # todo: Remove capex!!!
        if method == 'ic':
            role = ['in', 'ex']
        elif method == 'ic-op':
            role = ['in', 'ex']
            activity = ['op']
        elif method == 'ic-inv':
            role = ['in', 'ex']
            activity = ['inv']
        elif method == 'ic-fin':
            role = ['in', 'ex']
            activity = ['fin']

        je_txs = self.get_jes_tx_df(activity=activity, role=role, account=account)

        if not je_txs.empty:

            # Comment: Looking for the min & max dates of all JE's & transactions for index.
            i_start = je_txs[['pe_start', 'pe_finish']].min().min().date()
            i_finish = je_txs[['pe_start', 'pe_finish']].max().max().date()

            # Comment: If horizon for model, trim index.
            # if i_finish.year - i_start.year > self.years_horizon:
            #     i_finish = i_start + relativedelta(years=self.years_horizon)

            # Creating empty DF with the index.
            index = pd.DatetimeIndex(start=i_start, end=i_finish, freq='m')
            df = pd.DataFrame(index=index)

            for row in je_txs.iterrows():
                freq = row[1]['freq']
                if freq == 'nr':
                    iter_index = pd.DatetimeIndex(start=row[1]['pe_start'], end=row[1]['pe_start'], freq='m')
                elif freq[0] == 's':

                    if freq[1] == 'y':
                        offset = MonthEnd(12)
                        iter_index = pd.DatetimeIndex(start=row[1]['pe_start'], end=row[1]['pe_finish'],
                                                      freq=offset)
                    else:
                        iter_index = pd.DatetimeIndex(start=row[1]['pe_start'], end=row[1]['pe_finish'],
                                                      freq=row[1]['freq'][1])
                else:
                    iter_index = pd.DatetimeIndex(start=row[1]['pe_start'], end=row[1]['pe_finish'],
                                                  freq=row[1]['freq'])

                idx_df = pd.DataFrame(index=iter_index)

                if row[1]['freq'][0] == 's':
                    amount = pd.DataFrame(eval(row[1]['params'])['series'], index=iter_index).iloc[:, 0]
                else:
                    amount = row[1]['amount']

                if row[1]['tx_type'] == row[1]['balance_type']:
                    idx_df[row[1]['code']] = pd.to_numeric(amount)
                else:
                    idx_df[row[1]['code']] = -pd.to_numeric(amount)

                df = pd.concat([df, idx_df], axis=1)

            df = df.transpose()
            df.index.rename('code', inplace=True)
            df = df.groupby('code').sum()

            df = pd.merge(left=get_acc_idx(), right=df, how='inner', left_index=True, right_index=True)
            df.fillna(value=0, inplace=True)
            df.columns.name = 'timestamp'

        else:
            return pd.DataFrame()

        if to_json is True:
            if cum is True:
                return_df = df.cumsum().stack()
            else:
                return_df = df.stack()
            return_df = return_df.to_json(orient='index', date_format='iso')
            # return_df = return_df.rename(columns={'level_7': 'period', 0: 'amount'}).to_json(date_format='iso')
            return return_df
        else:
            if cum is True:
                return df.cumsum(axis=1)
            else:
                return df

    # Financial Statements -----

    def balance_sheet(self, cum=True, signs=False, to_json=False, activity=None):

        bs_df = self.get_ts_df(cum=cum, activity=activity, method='bs')

        if signs is True:

            def fcst_bs_xform(df_row):
                idx = [x.lower() for x in df_row.name]
                if 'assets' in idx and 'credit' in idx:
                    df_row = -df_row
                if ('liabilities' in idx or 'equity' in idx or 'other' in idx) and 'debit' in idx:
                    df_row = -df_row
                return df_row

            bs_df = bs_df.apply(fcst_bs_xform, axis=1)

        if to_json is True:
            bs_df = bs_df.stack()
            bs_df.name = 'amount'
            bs_df = bs_df.reset_index()
            return bs_df.to_json(orient='records', date_format='iso')
        else:
            return bs_df

    def income_statement(self, cum=True, signs=False, to_json=False, activity=None):

        method = 'ic'
        if isinstance(activity, str):
            method += '-{x1}'.format(x1=activity)

        ic_df = self.get_ts_df(cum=cum, method=method)

        if signs is True:
            # fixme: change to appropiate function
            def fcst_ic_xform(df_row):
                idx = [x.lower() for x in df_row.name]
                if 'assets' in idx and 'credit' in idx:
                    df_row = -df_row
                if ('liabilities' in idx or 'equity' in idx or 'other' in idx) and 'debit' in idx:
                    df_row = -df_row
                return df_row

            ic_df = ic_df.apply(fcst_ic_xform, axis=1)

        if to_json is True:
            return ic_df.stack().to_json(orient='index', date_format='iso')
        else:
            return ic_df

    def income(self, activity=None):
        inc_df = self.income_statement(cum=False, signs=True, to_json=False, activity=activity).sum()
        return inc_df

    # def acc_balance(self, acc_code, date):
    #     acc_code = str(acc_code)
    #     ts_df = self.get_ts_df().stack()
    #     ts_df.index.rename('timestamp', level=7, inplace=True)
    #     ts_df.name = 'balance'
    #     ts_df = ts_df.reset_index()[['acc_code', 'timestamp', 'balance']]
    #     ts_df.set_index(keys=['acc_code', 'timestamp'], inplace=True)
    #     balance = ts_df.loc[acc_code].loc[date]['balance'][-1]
    #     return balance

    def get_accout_balance(self, acc_code, period):
        return self.get_ts_df(account=acc_code).iloc[0][period].iloc[0]

