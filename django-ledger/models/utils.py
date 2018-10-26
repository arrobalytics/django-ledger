from django_pandas.io import read_frame
from pandas import merge

from .accounts import AccountModel
from .coa import CHART_OF_ACCOUNTS


# todo: Add CoA Support
def get_acc_idx():
    accounts = AccountModel.objects.all()
    acc_idx = read_frame(accounts,
                         fieldnames=['role_bs', 'parent', 'code', 'role', 'name',
                                     'balance_type'])
    parents = acc_idx[acc_idx['parent'] == acc_idx['code']][['code', 'name']]
    parents.rename(columns={'name': 'parent_name', 'code': 'parent_code'}, inplace=True)
    acc_idx = acc_idx[acc_idx['parent'] != acc_idx['code']]
    acc_idx = merge(left=acc_idx, right=parents, left_on='parent', right_on='parent_code')
    acc_idx.drop('parent', axis=1, inplace=True)
    acc_idx['balance_type'] = acc_idx['balance_type'].str.lower()
    acc_idx['role_bs'] = acc_idx['role_bs'].str.upper()
    acc_idx.set_index(keys=['role_bs', 'parent_code', 'parent_name',
                            'role', 'code', 'name', 'balance_type'],
                      inplace=True)
    acc_idx.sort_index(inplace=True)
    return acc_idx


class COAUtils(object):

    def account_update(self, account, data):
        """
        account: An instance of AccountModel
        data: a dictionary
        """
        account.code = data['acc_code']
        account.parent = data['acc_parent']
        account.name = data['acc_name']
        account.role = data['acc_role']
        account.balance_type = data['acc_type']
        account.clean()
        account.save()

    # fixme: Hitting database twice when creating accounts!!!
    def refresh_coa(self, force=False):

        for data in CHART_OF_ACCOUNTS.values():

            account, created = AccountModel.objects.get_or_create(code=data['acc_code'])

            if force is True:
                self.account_update(account, data)
                if created is True:
                    print('Account {x1} - {x2} has been created'.format(x1=account.code, x2=account.desc))
                else:
                    print('Account {x1} - {x2} has been updated'.format(x1=account.code, x2=account.desc))
            else:
                if created is True:
                    self.account_update(account, data)
                    print('Account {x1} - {x2} has been created'.format(x1=account.code, x2=account.name))
                else:
                    print('Account {x1} - {x2} already in DB'.format(x1=account.code, x2=account.name))
