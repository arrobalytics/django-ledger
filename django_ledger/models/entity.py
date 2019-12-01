from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse

from django_ledger.models.accounts import AccountModel
from django_ledger.models.mixins import io
from django_ledger.models.mixins.base import CreateUpdateMixIn, SlugNameMixIn

UserModel = get_user_model()


class EntityModel(SlugNameMixIn, CreateUpdateMixIn, io.IOMixIn):
    admin = models.ForeignKey(UserModel, on_delete=models.PROTECT, related_name='entities_admin')
    managers = models.ManyToManyField(UserModel, through='EntityManagementModel', related_name='entities_managed')
    coa = models.ForeignKey('django_ledger.ChartOfAccountModel',
                            on_delete=models.DO_NOTHING,
                            verbose_name='Chart of Accounts')

    class Meta:
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'

    def __str__(self):
        return '{x1} ({x2})'.format(x1=self.name,
                                    x2=self.slug)

    def get_absolute_url(self):
        return reverse('django_ledger:entity-detail',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_balance_sheet_url(self):
        return reverse('django_ledger:entity-balance-sheet',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_accounts(self):
        return AccountModel.on_coa.available(coa=self.coa)


class EntityManagementModel(CreateUpdateMixIn):
    PERMISSIONS = [
        ('read', 'Read Permissions'),
        ('write', 'Read/Write Permissions'),
        ('suspended', 'No Permissions')
    ]

    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name='Entity',
                               related_name='entity_permissions')
    user = models.ForeignKey(UserModel,
                             on_delete=models.CASCADE,
                             verbose_name='Manager',
                             related_name='entity_permissions')

    permission_level = models.CharField(max_length=10, default='read', choices=PERMISSIONS)
