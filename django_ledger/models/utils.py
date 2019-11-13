from pandas import DataFrame

from django_ledger.models.accounts import AccountModel


def find_parent(acc, par):
    for p in par:
        if acc.get('parent_id') == p.get('id'):
            return p


def acc_mapper(acc, parents):
    parent_acc = find_parent(acc, parents)
    if parent_acc:
        mapped_acc = dict()
        mapped_acc['role_bs'] = acc.get('role_bs').upper()
        mapped_acc['parent_code'] = parent_acc.get('code')
        mapped_acc['parent_name'] = parent_acc.get('name').upper()
        mapped_acc['code'] = acc.get('code')
        mapped_acc['role'] = acc.get('role').upper()
        mapped_acc['name'] = acc.get('name')
        mapped_acc['balance_type'] = acc.get('balance_type')
        return mapped_acc
    else:
        print(acc)


def get_acc_idx(coa, as_dataframe=False):
    qs_acc = AccountModel.objects.filter(coa_assignments__coa=coa)
    accounts = qs_acc.values('id',
                             'code',
                             'name',
                             'parent_id',
                             'role',
                             'role_bs',
                             'balance_type')
    parents = [acc for acc in accounts if acc.get('parent_id') is None]
    children = [acc for acc in accounts if acc.get('parent_id') is not None]

    acc_idx = [acc_mapper(acc, parents) for acc in children]
    if as_dataframe:
        acc_idx = DataFrame(acc_idx).set_index(keys=['role_bs', 'parent_code', 'parent_name', 'role', 'code', 'name',
                                                     'balance_type'])
    return acc_idx

# def get_acc_idx():
#     accounts = AccountModel.objects.all()
#     acc_idx = read_frame(accounts,
#                          fieldnames=['role_bs', 'parent', 'parent__code', 'code', 'role', 'name',
#                                      'balance_type'])
#     acc_idx.rename(columns={'parent__code': 'parent_code'}, inplace=True)
#     parents = acc_idx[acc_idx['parent'].isnull()][['code', 'name']]
#     parents.rename(columns={'name': 'parent_name', 'code': 'parent_code'}, inplace=True)
#     acc_idx = acc_idx[acc_idx['parent'].notnull()]
#     acc_idx = merge(left=acc_idx, right=parents, left_on='parent_code', right_on='parent_code')
#     acc_idx.drop('parent', axis=1, inplace=True)
#     acc_idx['balance_type'] = acc_idx['balance_type'].str.lower()
#     acc_idx['role_bs'] = acc_idx['role_bs'].str.upper()
#     acc_idx.set_index(keys=['role_bs', 'parent_code', 'parent_name',
#                             'role', 'code', 'name', 'balance_type'],
#                       inplace=True)
#     acc_idx.sort_index(inplace=True)
#     return acc_idx

# class COAUtils(object):
#
#     def account_update(self, account, data):
#         """
#         account: An instance of AccountModel
#         data: a dictionary
#         """
#         account.code = data['acc_code']
#         account.parent = data['acc_parent']
#         account.name = data['acc_name']
#         account.role = data['acc_role']
#         account.balance_type = data['acc_type']
#         account.clean()
#         account.save()
#
#     def refresh_coa(self, force=False):
#
#         for data in CHART_OF_ACCOUNTS.values():
#
#             account, created = AccountModel.objects.get_or_create(code=data['acc_code'])
#
#             if force is True:
#                 self.account_update(account, data)
#                 if created is True:
#                     print('Account {x1} - {x2} has been created'.format(x1=account.code, x2=account.desc))
#                 else:
#                     print('Account {x1} - {x2} has been updated'.format(x1=account.code, x2=account.desc))
#             else:
#                 if created is True:
#                     self.account_update(account, data)
#                     print('Account {x1} - {x2} has been created'.format(x1=account.code, x2=account.name))
#                 else:
#                     print('Account {x1} - {x2} already in DB'.format(x1=account.code, x2=account.name))
