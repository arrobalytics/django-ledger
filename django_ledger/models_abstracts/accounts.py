from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from mptt.models import MPTTModel, TreeForeignKey

from django_ledger.models.mixins.base import CreateUpdateMixIn
from django_ledger.settings import DJANGO_LEDGER_ACCOUNT_MAX_LENGTH

ACCOUNT_ROLES = [
    ('Assets', (
        ('ca', _('Current Asset')),
        ('lti', _('Long Term Investments')),
        ('ppe', _('Property Plant & Equipment')),
        ('ia', _('Intangible Assets')),
        ('aadj', _('Asset Adjustments')),
    )
     ),
    ('Liabilities', (
        ('cl', _('Current Liabilities')),
        ('ltl', _('Long Term Liabilities')),
    )
     ),
    ('Equity', (
        ('cap', _('Capital')),
        ('cadj', _('Capital Adjustments')),
        ('in', _('Income')),
        ('ex', _('Expense')),
    )
     ),
    ('Other', (
        ('excl', _('Excluded')),
    )
     )
]

ROLE_TUPLES = sum([[(r[0].lower(), s[0]) for s in r[1]] for r in ACCOUNT_ROLES], list())
VALID_ROLES = [r[1] for r in ROLE_TUPLES]
BS_ROLES = dict([(r[1], r[0]) for r in ROLE_TUPLES])


def validate_roles(roles):
    if roles:
        if isinstance(roles, str):
            roles = [roles]
        for r in roles:
            if r not in VALID_ROLES:
                raise ValidationError('{roles}) is invalid. Choices are {ch}'.format(ch=', '.join(VALID_ROLES),
                                                                                     roles=r))
    return roles


class AccountModelManager(models.Manager):

    def for_user(self, user):
        qs = self.get_queryset()
        return qs.filter(
            Q(coa__entity__admin=user) |
            Q(coa__entity__managers__exact=user)
        )

    def available(self, coa):
        return self.get_queryset().filter(
            active=True,
            locked=False,
            coa=coa
        )


class AccountModelAbstract(MPTTModel, CreateUpdateMixIn):
    BALANCE_TYPE = [
        ('credit', _('Credit')),
        ('debit', _('Debit'))
    ]

    code = models.CharField(max_length=DJANGO_LEDGER_ACCOUNT_MAX_LENGTH,
                            unique=True, verbose_name=_l('Account Code'))
    name = models.CharField(max_length=100, verbose_name=_l('Account Name'))
    role = models.CharField(max_length=10, choices=ACCOUNT_ROLES, verbose_name=_l('Account Role'))
    balance_type = models.CharField(max_length=6, choices=BALANCE_TYPE, verbose_name=_('Account Balance Type'))
    parent = TreeForeignKey('self',
                            null=True,
                            blank=True,
                            related_name='children',
                            verbose_name=_l('Parent'),
                            db_index=True,
                            on_delete=models.CASCADE)
    locked = models.BooleanField(default=False, verbose_name=_l('Locked'))
    active = models.BooleanField(default=False, verbose_name=_l('Active'))
    coa = models.ForeignKey('django_ledger.ChartOfAccountModel',
                            on_delete=models.CASCADE,
                            verbose_name=_l('Chart of Accounts'),
                            related_name='accounts')
    on_coa = AccountModelManager()

    class Meta:
        # todo: add ordering to all models
        abstract = True
        verbose_name = _l('Account')
        verbose_name_plural = _l('Accounts')
        unique_together = [
            ('coa', 'code')
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

    def get_update_url(self, entity_slug=None, coa_slug=None):
        if not entity_slug:
            entity_slug = self.coa.entity.slug
        if not coa_slug:
            coa_slug = self.coa.slug
        return reverse('django_ledger:account-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'coa_slug': coa_slug,
                           'account_pk': self.id
                       })

    def get_create_url(self, entity_slug=None, coa_slug=None):
        if not entity_slug:
            entity_slug = self.coa.entity.slug
        if not coa_slug:
            coa_slug = self.coa.slug
        return reverse('django_ledger:account-create',
                       kwargs={
                           'entity_slug': entity_slug,
                           'coa_slug': coa_slug,
                           'account_pk': self.id
                       })

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
            raise ValidationError(_l('Account code must not contain spaces'))
