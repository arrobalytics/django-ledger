from django.db import models
from django_pandas.io import read_frame
from jsonfield import JSONField
from pandas import merge

from books.coa import CHART_OF_ACCOUNTS
from books.models.accounts import AccountModel


class ChartOfAccountsModel(models.Model):
    desc = models.CharField(max_length=20, unique=True)
    coa = JSONField(default=CHART_OF_ACCOUNTS)

    # todo: this is a duplicate from fcts model.
    def get_accounts_index_df(self):
        accounts = AccountModel.objects.all()
        accounts_df = read_frame(accounts,
                                 fieldnames=['acc_role_bs', 'acc_parent', 'acc_code', 'acc_role', 'acc_desc',
                                             'acc_type'])
        parents_df = accounts_df[accounts_df['acc_parent'] == accounts_df['acc_code']][['acc_code', 'acc_desc']]
        parents_df.rename(columns={'acc_desc': 'parent_desc', 'acc_code': 'parent_code'}, inplace=True)
        accounts_df = accounts_df[accounts_df['acc_parent'] != accounts_df['acc_code']]
        accounts_df = merge(left=accounts_df, right=parents_df, left_on='acc_parent', right_on='parent_code')
        accounts_df.drop('acc_parent', axis=1, inplace=True)
        accounts_df['acc_type'] = accounts_df['acc_type'].str.lower()
        accounts_df['acc_role_bs'] = accounts_df['acc_role_bs'].str.upper()
        accounts_df.set_index(keys=['acc_role_bs', 'parent_code', 'parent_desc',
                                    'acc_role', 'acc_code', 'acc_desc', 'acc_type'],
                              inplace=True)
        accounts_df.sort_index(inplace=True)
        return accounts_df

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)
