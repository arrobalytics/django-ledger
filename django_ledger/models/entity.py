"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from calendar import monthrange
from datetime import date
from random import choices
from string import ascii_lowercase, digits
from typing import Tuple
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Manager, Q
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from django_ledger.io import IOMixIn
from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn, ContactInfoMixIn, NodeTreeMixIn

UserModel = get_user_model()

ENTITY_RANDOM_SLUG_SUFFIX = ascii_lowercase + digits


class EntityReportManager:
    VALID_QUARTERS = list(range(1, 5))

    def get_fy_start_month(self) -> int:
        fy = getattr(self, 'fy_start_month', None)
        if not fy:
            return 1
        return fy

    def validate_quarter(self, quarter: int):
        if quarter not in self.VALID_QUARTERS:
            raise ValidationError(f'Specified quarter is not valid: {quarter}')

    def get_fy_start(self, year: int, fy_start_month: int = None) -> date:
        fy_start_month = self.get_fy_start_month() if not fy_start_month else fy_start_month
        return date(year, fy_start_month, 1)

    def get_fy_end(self, year: int, fy_start_month: int = None) -> date:
        fy_start_month = self.get_fy_start_month() if not fy_start_month else fy_start_month
        ye = year if fy_start_month == 1 else year + 1
        me = 12 if fy_start_month == 1 else fy_start_month - 1
        return date(ye, me, monthrange(ye, me)[1])

    def get_quarter_start(self, year: int, quarter: int, fy_start_month: int = None) -> date:
        fy_start_month = self.get_fy_start_month() if not fy_start_month else fy_start_month
        quarter_month_start = (quarter - 1) * 3 + fy_start_month
        year_start = year
        if quarter_month_start > 12:
            quarter_month_start -= 12
            year_start = year + 1
        return date(year_start, quarter_month_start, 1)

    def get_quarter_end(self, year: int, quarter: int, fy_start_month: int = None) -> date:
        fy_start_month = self.get_fy_start_month() if not fy_start_month else fy_start_month
        quarter_month_end = quarter * 3 + fy_start_month - 1
        year_end = year
        if quarter_month_end > 12:
            quarter_month_end -= 12
            year_end += 1
        return date(year_end, quarter_month_end, monthrange(year_end, quarter_month_end)[1])

    def get_fiscal_year_dates(self, year: int, fy_start_month: int = None) -> Tuple[date, date]:
        sd = self.get_fy_start(year, fy_start_month)
        ed = self.get_fy_end(year, fy_start_month)
        return sd, ed

    def get_fiscal_quarter_dates(self, year: int, quarter: int, fy_start_month: int = None) -> Tuple[date, date]:
        self.validate_quarter(quarter)
        qs = self.get_quarter_start(year, quarter, fy_start_month)
        qe = self.get_quarter_end(year, quarter, fy_start_month)
        return qs, qe


class EntityModelManager(Manager):

    def for_user(self, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(admin=user_model) |
            Q(managers__in=[user_model])
        )


class EntityModelAbstract(NodeTreeMixIn,
                          SlugNameMixIn,
                          CreateUpdateMixIn,
                          ContactInfoMixIn,
                          IOMixIn,
                          EntityReportManager):
    FY_MONTHS = [
        (1, _('January')),
        (2, _('February')),
        (3, _('March')),
        (4, _('April')),
        (5, _('May')),
        (6, _('June')),
        (7, _('July')),
        (8, _('August')),
        (9, _('September')),
        (10, _('October')),
        (11, _('November')),
        (12, _('December')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=150, verbose_name=_('Entity Name'), null=True, blank=True)
    admin = models.ForeignKey(UserModel,
                              on_delete=models.CASCADE,
                              related_name='admin_of',
                              verbose_name=_('Admin'))
    managers = models.ManyToManyField(UserModel, through='EntityManagementModel',
                                      related_name='managed_by', verbose_name=_('Managers'))

    hidden = models.BooleanField(default=False)
    fy_start_month = models.IntegerField(choices=FY_MONTHS, default=1, verbose_name=_('Fiscal Year Start'))
    objects = EntityModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Entity')
        verbose_name_plural = _('Entities')
        indexes = [
            models.Index(fields=['admin']),
            models.Index(fields=['parent'])
        ]

    def __str__(self):
        return self.name

    def get_dashboard_url(self):
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_manage_url(self):
        return reverse('django_ledger:entity-update',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_ledgers_url(self):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_bills_url(self):
        return reverse('django_ledger:bill-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_invoices_url(self):
        return reverse('django_ledger:invoice-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_banks_url(self):
        return reverse('django_ledger:bank-account-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_balance_sheet_url(self):
        return reverse('django_ledger:entity-bs',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_income_statement_url(self):
        return reverse('django_ledger:entity-ic',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_data_import_url(self):
        return reverse('django_ledger:data-import-jobs-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_accounts_url(self):
        return reverse('django_ledger:account-list',
                       kwargs={
                           'entity_slug': self.slug,
                       })

    def get_customers_url(self):
        return reverse('django_ledger:customer-list',
                       kwargs={
                           'entity_slug': self.slug,
                       })

    def get_vendors_url(self):
        return reverse('django_ledger:vendor-list',
                       kwargs={
                           'entity_slug': self.slug,
                       })

    def get_delete_url(self):
        return reverse('django_ledger:entity-delete',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_fy_start_month(self) -> int:
        return self.fy_start_month

    def clean(self):
        if not self.name:
            raise ValidationError(message=_('Must provide a name for EntityModel'))

        if not self.slug:
            slug = slugify(self.name)
            suffix = ''.join(choices(ENTITY_RANDOM_SLUG_SUFFIX, k=6))
            entity_slug = f'{slug}-{suffix}'
            self.slug = entity_slug


class EntityManagementModelAbstract(CreateUpdateMixIn):
    """
    Entity Management Model responsible for manager permissions to read/write.
    """
    PERMISSIONS = [
        ('read', _('Read Permissions')),
        ('write', _('Read/Write Permissions')),
        ('suspended', _('No Permissions'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Entity'),
                               related_name='entity_permissions')
    user = models.ForeignKey(UserModel,
                             on_delete=models.CASCADE,
                             verbose_name=_('Manager'),
                             related_name='entity_permissions')
    permission_level = models.CharField(max_length=10,
                                        default='read',
                                        choices=PERMISSIONS,
                                        verbose_name=_('Permission Level'))

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['entity', 'user']),
            models.Index(fields=['user', 'entity'])
        ]


class EntityModel(EntityModelAbstract):
    """
    Entity Model Base Class From Abstract
    """


def entitymodel_postsave(instance, **kwargs):
    if not getattr(instance, 'coa', None):
        ChartOfAccountModel.objects.create(
            slug=instance.slug + '-coa',
            name=instance.name + ' CoA',
            entity=instance
        )
        instance.ledgermodel_set.create(
            name=_(f'{instance.name} General Ledger'),
            posted=True
        )


post_save.connect(entitymodel_postsave, EntityModel)


class EntityManagementModel(EntityManagementModelAbstract):
    """
    EntityManagement Model Base Class From Abstract
    """
