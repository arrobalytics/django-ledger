from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from pandas import DataFrame

from django_ledger.models.accounts import AccountModel
from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn


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
    qs = coa_model.acc_assignments.all()
    account_assignment = qs.filter(account__code__in=account_codes)
    account_assignment.update(active=True)


class ChartOfAccountModelAbstract(SlugNameMixIn,
                                  CreateUpdateMixIn):
    desc = models.TextField(verbose_name='CoA Description', null=True, blank=True)
    accounts = models.ManyToManyField('django_ledger.AccountModel',
                                      related_name='coas',
                                      through='CoAAccountAssignments')

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.slug}: {self.name}'

    def get_coa_account(self, code):
        try:
            qs = self.acc_assignments.available()
            acc_model = qs.get(account__code__iexact=code)
            return acc_model
        except ObjectDoesNotExist:
            raise ValueError(
                'Account {acc} is either not assigned, inactive, locked or non existent for CoA: {coa}'.format(
                    acc=code,
                    coa=self.__str__()
                ))

    def get_accounts_index(self, as_dataframe=False):
        idx = get_acc_idx(self, as_dataframe=as_dataframe)
        return idx


class ChartOfAccountModel(ChartOfAccountModelAbstract):
    """
    Final ChartOfAccountsModel from Abstracts
    """

    class Meta:
        verbose_name = 'Chart of Account'


class AccountAssignmentsManager(models.Manager):

    def available(self):
        return self.get_queryset().filter(locked=False, active=True)

    def inactive(self):
        return self.get_queryset().filter(active=False)

    def active(self):
        return self.get_queryset().filter(active=True)

    def locked(self):
        return self.get_queryset().filter(locked=True)

    def unlocked(self):
        return self.get_queryset().filter(locked=False)


class CoAAccountAssignments(models.Model):
    account = models.ForeignKey('django_ledger.AccountModel',
                                on_delete=models.CASCADE,
                                verbose_name='Accounts',
                                related_name='coa_assignments')

    coa = models.ForeignKey('django_ledger.ChartOfAccountModel',
                            on_delete=models.CASCADE,
                            verbose_name='Chart of Accounts',
                            related_name='acc_assignments')

    locked = models.BooleanField(default=False)
    active = models.BooleanField(default=False)

    objects = AccountAssignmentsManager()

    def __str__(self):
        return '{coa}: {acc}'.format(coa=self.coa.__str__(),
                                     acc=self.account.__str__()
                                     )

    class Meta:
        verbose_name = 'Chart of Account Assignment'
        unique_together = [
            ('account', 'coa')
        ]
