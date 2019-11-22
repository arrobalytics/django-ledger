from django.db import models

from django_ledger.models.accounts import AccountModel
from django_ledger.models.mixins import io
from django_ledger.models.mixins.base import CreateUpdateMixIn, SlugNameMixIn


class EntityModelAbstract(SlugNameMixIn, CreateUpdateMixIn, io.IOMixIn):
    coa = models.ForeignKey('django_ledger.ChartOfAccountModel',
                            on_delete=models.DO_NOTHING,
                            verbose_name='Chart of Accounts')

    class Meta:
        abstract = True

    def __str__(self):
        return '{x1} ({x2})'.format(x1=self.name,
                                    x2=self.slug)

    def get_accounts(self):
        return AccountModel.on_coa.available(coa=self.coa)


class EntityModel(EntityModelAbstract):
    """
    Final EntityModel from Abstracts
    """

    class Meta:
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'
