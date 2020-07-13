from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

from django_ledger.io.roles import ACCOUNT_ROLES, BS_ROLES
from django_ledger.models.mixins import CreateUpdateMixIn


class AccountModelManager(models.Manager):

    def for_entity(self, user_model, entity_slug: str, coa_slug: str = None):
        qs = self.get_queryset()
        qs = qs.filter(
            Q(coa__entity__slug__exact=entity_slug) &
            (
                    Q(coa__entity__admin=user_model) |
                    Q(coa__entity__managers__in=[user_model])
            )
        ).order_by('code')
        # todo: I don't like this... coa_slug is optional but necessary for any account operations. not for txs..?
        # it's highly unlikely that an entity will have multiple CoA's given the one-to-one relationship between them...
        if coa_slug:
            qs = qs.filter(coa__slug__iexact=coa_slug)
        return qs

    def for_entity_available(self, user_model, entity_slug: str, coa_slug: str = None):
        qs = self.for_entity(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(
            active=True,
            locked=False
        )


class AccountModelAbstract(MPTTModel, CreateUpdateMixIn):
    """
    Djetler's Base Account Model Abstract
    """
    BALANCE_TYPE = [
        ('credit', _('Credit')),
        ('debit', _('Debit'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    code = models.CharField(max_length=10, verbose_name=_('Account Code'))
    name = models.CharField(max_length=100, verbose_name=_('Account Name'))
    role = models.CharField(max_length=25, choices=ACCOUNT_ROLES, verbose_name=_('Account Role'))
    balance_type = models.CharField(max_length=6, choices=BALANCE_TYPE, verbose_name=_('Account Balance Type'))
    parent = TreeForeignKey('self',
                            null=True,
                            blank=True,
                            related_name='children',
                            verbose_name=_('Parent'),
                            db_index=True,
                            on_delete=models.CASCADE)
    locked = models.BooleanField(default=False, verbose_name=_('Locked'))
    active = models.BooleanField(default=False, verbose_name=_('Active'))
    coa = models.ForeignKey('django_ledger.ChartOfAccountModel',
                            on_delete=models.CASCADE,
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

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return '{x1} - {x5}: {x2} ({x3}/{x4})'.format(x1=self.role_bs.upper(),
                                                      x2=self.name,
                                                      x3=self.role.upper(),
                                                      x4=self.balance_type,
                                                      x5=self.code)

    @property
    def role_bs(self):
        return BS_ROLES.get(self.role)

    def get_balance(self):

        credits = self.txs.filter(
            tx_type__exact='credit').aggregate(
            credits=Coalesce(Sum('amount'), 0))['credits']

        debits = self.txs.filter(
            tx_type__exact='debit').aggregate(
            debits=Coalesce(Sum('amount'), 0))['debits']

        if self.balance_type == 'credit':
            return credits - debits
        elif self.balance_type == 'debit':
            return debits - credits

    def clean(self):
        if ' ' in self.code:
            raise ValidationError(_('Account code must not contain spaces'))


class AccountModel(AccountModelAbstract):
    """
    Base Account Model from Account Model Abstract Class
    """
