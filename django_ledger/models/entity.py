from random import randint

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from django_ledger.models.accounts import AccountModel
from django_ledger.models.mixins.base import CreateUpdateMixIn, SlugNameMixIn
from django_ledger.models.mixins.io import IOMixIn

UserModel = get_user_model()


class EntityModel(SlugNameMixIn,
                  CreateUpdateMixIn,
                  IOMixIn):
    admin = models.ForeignKey(UserModel, on_delete=models.PROTECT,
                              related_name='admin_of', verbose_name=_l('Admin'))
    managers = models.ManyToManyField(UserModel, through='EntityManagementModel',
                                      related_name='managed_by', verbose_name=_l('Managers'))
    coa = models.OneToOneField('django_ledger.ChartOfAccountModel',
                               on_delete=models.CASCADE,
                               related_name='entity',
                               verbose_name=_l('Chart of Accounts'))

    class Meta:
        verbose_name = _l('Entity')
        verbose_name_plural = _l('Entities')  # idea: can use th django plural function...

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

    def get_income_statement_url(self):
        return reverse('django_ledger:entity-income-statement',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_ledgers_url(self):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_accounts(self):
        return AccountModel.on_coa.available(coa=self.coa)


def entity_presave(sender, instance, **kwargs):
    if not instance.slug:
        slug = slugify(instance.name)
        ri = randint(100000, 999999)
        entity_slug = f'{slug}-{ri}'
        instance.slug = entity_slug


pre_save.connect(entity_presave, EntityModel)


class EntityManagementModel(CreateUpdateMixIn):
    PERMISSIONS = [
        ('read', _('Read Permissions')),
        ('write', _('Read/Write Permissions')),
        ('suspended', _('No Permissions'))
    ]

    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_l('Entity'),
                               related_name='entity_permissions')
    user = models.ForeignKey(UserModel,
                             on_delete=models.CASCADE,
                             verbose_name=_l('Manager'),
                             related_name='entity_permissions')
    permission_level = models.CharField(max_length=10,
                                        default='read',
                                        choices=PERMISSIONS,
                                        verbose_name=_l('Permission Level'))
