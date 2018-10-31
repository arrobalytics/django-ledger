from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn
from django_ledger.models.utils import get_acc_idx


class ChartOfAccountModelAbstract(SlugNameMixIn,
                                  CreateUpdateMixIn):
    desc = models.TextField(verbose_name='CoA Description')
    accounts = models.ManyToManyField('django_ledger.AccountModel',
                                      related_name='coas',
                                      through='CoAAccountAssignments')

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def get_accounts_index(self, as_dataframe=False):
        idx = get_acc_idx(self, as_dataframe=as_dataframe)
        return idx


def get_coa_account(coa_model, code):
    try:
        qs = coa_model.acc_assignments.available()
        acc_model = qs.get(account__code__iexact=code)
        return acc_model
    except ObjectDoesNotExist:
        raise ValueError('Account {acc} is either not assigned, inactive, locked or non existent for CoA: {coa}'.format(
            acc=code,
            coa=coa_model.__str__()
        ))


class AccountAssignmentsManager(models.Manager):

    def available(self):
        return self.get_queryset().filter(locked=False,
                                          active=True)

    def inactive(self):
        return self.get_queryset().filter(active=False)

    def active(self):
        return self.get_queryset().filter(active=True)

    def locked(self):
        return self.get_queryset().filter(locked=True)

    def unlocked(self):
        return self.get_queryset().filter(locked=False)


class CoAAccountAssignments(models.Model):
    # todo: add unique coa-acccode index.

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
        indexes = [
            models.Index(fields=[
                'account',
                'coa'
            ])
        ]


class ChartOfAccountModel(ChartOfAccountModelAbstract):
    """
    Final ChartOfAccountsModel from Abstracts
    """

    class Meta:
        verbose_name = 'Chart of Account'
