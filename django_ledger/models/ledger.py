import calendar
from collections import namedtuple, OrderedDict
from datetime import datetime
from random import randint

import pandas as pd
from django.db import models
from django.db.models.signals import pre_save
from django.utils.text import slugify

from django_ledger.models.accounts import AccountModel
from django_ledger.models.accounts import validate_roles
from django_ledger.models.coa import get_coa_account, get_acc_idx
from django_ledger.models.io.generic import IOGenericMixIn
from django_ledger.models.io.preproc import IOPreProcMixIn
from django_ledger.models.journalentry import validate_activity
from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn


def get_ledger_coa(ledger_model):
    """
    Utility function to get the associated ledger's Chart of Account model.
    :param ledger_model: A Ledger model instance
    :return:
    """
    return ledger_model.entity.coa


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


class LedgerModelManager(models.Manager):

    def posted(self):
        return self.get_queryset().filter(posted=True)


class LedgerModelAbstract(SlugNameMixIn,
                          CreateUpdateMixIn,
                          IOPreProcMixIn,
                          IOGenericMixIn):
    posted = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               related_name='general_ledger')

    objects = LedgerModelManager()

    class Meta:
        abstract = True

    def __str__(self):
        return '{slug}: {name}'.format(name=self.name,
                                       slug=self.slug)

    def get_coa(self):
        return self.entity.coa

    # TODO: This can be handled by the Model Manager...?
    def get_accounts(self, status='available'):
        choices = (
            'available',
            'inactive',
            'active',
            'locked',
            'unlocked'
        )
        if status not in choices:
            raise ValueError('Invalid account status.')
        # coa = self.get_coa()
        account_models = AccountModel.objects.filter(
            coa_assignments__active=True,
            coa_assignments__locked=False,
            coa_assignments__coa=self.get_coa()
        )
        return account_models
        # return getattr(coa.acc_assignments, status)()

    def get_account(self, code):
        """
        Convenience method to get an account model instance from the ledger entity Chart of Accounts.
        :param code: Account code.
        :return:
        """
        return get_coa_account(coa_model=self.get_coa(),
                               code=code)

    def get_jes_data(self, as_dataframe=False):
        jes = list(self.jes.all().values())
        if as_dataframe:
            jes = pd.DataFrame(jes)
            jes.rename(columns={'id': 'je_id'}, inplace=True)
            jes.set_index('je_id', inplace=True)
            jes['start_date'] = pd.to_datetime(jes['start_date'])
            jes['end_date'] = pd.to_datetime(jes['end_date'])
        return jes

    def get_je_txs(self, as_of: str = None, activity: str = None, role: str = None, account: str = None) -> list:

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

        field_map = OrderedDict({'id': 'je_id',
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

        db_fields = [k for k, _ in field_map.items()]
        new_fields = [v for _, v in field_map.items()]
        sd_idx = new_fields.index('date')
        jes_records = jes.values_list(*db_fields)
        jes_list = list()
        for jer in jes_records:
            date = jer[sd_idx]
            je_date = datetime(year=date.year,
                               month=date.month,
                               day=calendar.monthrange(date.year, date.month)[-1])
            jer = jer + (je_date,)
            jes_list.append(jer)
        new_fields.append('je_date')
        je_tuple = namedtuple('JERecord', ', '.join(new_fields))
        jes_records = [je_tuple(*je) for je in jes_list]
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

    def get_account_balance(self, account_code: str, as_of: str = None):
        return self.get_jes(account=account_code, as_of=as_of)


class LedgerModel(LedgerModelAbstract):
    """
    Final LedgerModel from Abstracts
    """


def ledgermodel_presave(sender, instance, **kwargs):
    if not instance.slug:
        r_int = randint(10000, 99999)
        slug = slugify(instance.name)
        instance.slug = f'{slug}-{r_int}'


pre_save.connect(ledgermodel_presave, LedgerModel)
