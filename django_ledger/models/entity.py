from .mixins import CreateUpdateMixIn, SlugNameMixIn
from django.db import models


class EntityModelAbstract(SlugNameMixIn,
                          CreateUpdateMixIn):
    coa = models.ForeignKey('django_ledger.ChartOfAccountModel',
                            on_delete=models.DO_NOTHING,
                            verbose_name='Chart of Accounts')

    class Meta:
        abstract = True

    def __str__(self):
        return '{x1} ({x2})'.format(x1=self.name,
                                    x2=self.slug)


class EntityModel(EntityModelAbstract):
    """
    Final EntityModel from Abstracts
    """

    class Meta:
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'
