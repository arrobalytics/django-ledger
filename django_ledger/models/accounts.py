"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from typing import Union
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ACCOUNT_ROLES, BS_ROLES, GROUP_INVOICE, GROUP_BILL
from django_ledger.models.mixins import CreateUpdateMixIn, ParentChildMixIn

DEBIT = 'debit'
CREDIT = 'credit'


class AccountModelQuerySet(models.QuerySet):

    def active(self):
        return self.filter(active=True)

    def with_roles(self, roles: Union[list, str]):
        if isinstance(roles, str):
            roles = [roles]
        return self.filter(role__in=roles)


class AccountModelManager(models.Manager):

    def get_queryset(self):
        return AccountModelQuerySet(self.model, using=self._db)

    def for_entity(self, user_model, entity_slug: str, coa_slug: str = None):
        qs = self.get_queryset()
        qs = qs.filter(
            Q(coa__entity__slug__exact=entity_slug) &
            (
                    Q(coa__entity__admin=user_model) |
                    Q(coa__entity__managers__in=[user_model])
            )
        ).order_by('code')
        if coa_slug:
            qs = qs.filter(coa__slug__iexact=coa_slug)
        return qs

    def with_roles(self, roles: Union[list, str], entity_slug: str, user_model):
        if isinstance(roles, str):
            roles = [roles]
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(role__in=roles)

    def with_roles_available(self, roles: Union[list, str], entity_slug: str, user_model):
        if isinstance(roles, str):
            roles = [roles]
        qs = self.for_entity_available(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(role__in=roles)

    def for_entity_available(self, user_model, entity_slug: str, coa_slug: str = None):
        qs = self.for_entity(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(
            active=True,
            locked=False
        )

    def for_invoice(self, user_model, entity_slug: str, coa_slug: str = None):
        qs = self.for_entity_available(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(role__in=GROUP_INVOICE)

    def for_bill(self, user_model, entity_slug: str, coa_slug: str = None):
        qs = self.for_entity_available(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(role__in=GROUP_BILL)


class AccountModelAbstract(ParentChildMixIn, CreateUpdateMixIn):
    """
    Djetler's Base Account Model Abstract
    """
    BALANCE_TYPE = [
        (CREDIT, _('Credit')),
        (DEBIT, _('Debit'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    code = models.CharField(max_length=10, verbose_name=_('Account Code'))
    name = models.CharField(max_length=100, verbose_name=_('Account Name'))
    role = models.CharField(max_length=25, choices=ACCOUNT_ROLES, verbose_name=_('Account Role'))
    balance_type = models.CharField(max_length=6, choices=BALANCE_TYPE, verbose_name=_('Account Balance Type'))
    locked = models.BooleanField(default=False, verbose_name=_('Locked'))
    active = models.BooleanField(default=False, verbose_name=_('Active'))
    coa = models.ForeignKey('django_ledger.ChartOfAccountModel',
                            on_delete=models.CASCADE,
                            editable=False,
                            verbose_name=_('Chart of Accounts'),
                            related_name='accounts')
    on_coa = AccountModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        unique_together = [
            ('coa', 'code')
        ]
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['balance_type']),
            models.Index(fields=['active']),
            models.Index(fields=['coa']),
            models.Index(fields=['role', 'balance_type', 'active']),
        ]

    def __str__(self):
        return '{x1} - {x5}: {x2} ({x3}/{x4})'.format(x1=self.role_bs.upper(),
                                                      x2=self.name,
                                                      # pylint: disable=no-member
                                                      x3=self.role.upper(),
                                                      x4=self.balance_type,
                                                      x5=self.code)

    @property
    def role_bs(self):
        return BS_ROLES.get(self.role)

    def is_debit(self):
        return self.balance_type == DEBIT

    def is_credit(self):
        return self.balance_type == CREDIT

    def clean(self):
        # pylint: disable=unsupported-membership-test
        if ' ' in self.code:
            raise ValidationError(_('Account code must not contain spaces'))


class AccountModel(AccountModelAbstract):
    """
    Base Account Model from Account Model Abstract Class
    """
