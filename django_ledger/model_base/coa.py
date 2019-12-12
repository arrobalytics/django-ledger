from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _l
from pandas import DataFrame

from django_ledger.models.accounts import AccountModel
from django_ledger.models.mixins.base import CreateUpdateMixIn, SlugNameMixIn

UserModel = get_user_model()


def get_coa_account(coa_model, code):
    try:
        qs = coa_model.acc_assignments.available()
        acc_model = qs.get(account__code__iexact=code)
        return acc_model
    except ObjectDoesNotExist:
        raise ValueError(
            'Account {acc} is either not assigned, inactive, locked or non existent for CoA: {coa}'.format(
                acc=code,
                coa=coa_model.__str__()
            ))


def get_acc_idx(coa_model, as_dataframe=False):
    qs_acc = AccountModel.objects.filter(coa_assignments__coa=coa_model)
    accounts = qs_acc.values('id',
                             'code',
                             'name',
                             'parent_id',
                             'role',
                             'role_bs',
                             'balance_type')
    parents = [acc for acc in accounts if not acc.get('parent_id')]
    children = [acc for acc in accounts if acc.get('parent_id')]
    acc_idx = [accounts_index(acc, parents) for acc in children]
    if as_dataframe:
        acc_idx = DataFrame(acc_idx).set_index(
            keys=['role_bs', 'parent_code', 'parent_name', 'role', 'code', 'name', 'balance_type'])
    return acc_idx


def find_parent(acc, par):
    return next(iter([p for p in par if acc.get('parent_id') == p.get('id')]))


def accounts_index(account_values, parents):
    parent_acc = find_parent(account_values, parents)
    if parent_acc:
        mapped_acc = dict()
        mapped_acc['role_bs'] = account_values.get('role_bs').upper()
        mapped_acc['parent_code'] = parent_acc.get('code')
        mapped_acc['parent_name'] = parent_acc.get('name').upper()
        mapped_acc['code'] = account_values.get('code')
        mapped_acc['role'] = account_values.get('role').upper()
        mapped_acc['name'] = account_values.get('name')
        mapped_acc['balance_type'] = account_values.get('balance_type')
        return mapped_acc


def make_account_active(coa_model, account_codes: str or list):
    if isinstance(account_codes, str):
        account_codes = [account_codes]
    qs = coa_model.accounts.all()
    acc = qs.filter(code__in=account_codes)
    acc.update(active=True)


class ChartOfAccountModelAbstract(SlugNameMixIn,
                                  CreateUpdateMixIn):
    description = models.TextField(verbose_name=_l('CoA Description'), null=True, blank=True)

    class Meta:
        abstract = True
        verbose_name = _l('Chart of Account')
        verbose_name_plural = _l('Chart of Accounts')

    def __str__(self):
        return f'{self.slug}: {self.name}'

    def get_absolute_url(self):
        return reverse('django_ledger:coa-detail',
                       kwargs={
                           'coa_slug': self.slug
                       })
