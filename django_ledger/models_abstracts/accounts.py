from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from mptt.models import MPTTModel, TreeForeignKey

from django_ledger.models.mixins.base import CreateUpdateMixIn
from django_ledger.models_abstracts import account_roles as roles

ACCOUNT_ROLES = [
    ('Assets', (
        # (roles.ROLE_PARENT_ASSET, _('Asset Account Parent')),

        (roles.ROLE_CA_CASH, _('Current Asset')),
        (roles.ROLE_CA_MKT_SECURITIES, _('Marketable Securities')),
        (roles.ROLE_CA_RECEIVABLES, _('Receivables')),
        (roles.ROLE_CA_INVENTORY, _('Inventory')),
        (roles.ROLE_CA_UNCOLLECTIBLES, _('Uncollectibles')),
        (roles.ROLE_CA_PREPAID, _('Prepaid')),
        (roles.ROLE_CA_OTHER, _('Other Liquid Assets')),

        (roles.ROLE_LTI_NOTES_RECEIVABLE, _('Notes Receivable')),
        (roles.ROLE_LTI_LAND, _('Land')),
        (roles.ROLE_LTI_SECURITIES, _('Securities')),

        # (roles.ROLE_LTI, _('Long Term Investments')),
        (roles.ROLE_PPE, _('Property Plant & Equipment')),
        (roles.ROLE_INTANGIBLE_ASSETS, _('Intangible Assets')),
        (roles.ROLE_ASSET_OTHER, _('Other Assets')),
    )
     ),
    ('Liabilities', (
        # (roles.ROLE_PARENT_LIABILITIES, _('Liability Account Parent')),
        (roles.ROLE_CL_ACC_PAYABLE, _('Accounts Payable')),
        (roles.ROLE_CL_WAGES_PAYABLE, _('Wages Payable')),
        (roles.ROLE_CL_INT_PAYABLE, _('Interest Payable')),
        (roles.ROLE_CL_ST_NOTES_PAYABLE, _('Notes Payable')),
        (roles.ROLE_CL_LTD_MATURITIES, _('Current Maturities of Long Tern Debt')),
        (roles.ROLE_CL_DEFERRED_REVENUE, _('Deferred Revenue')),
        (roles.ROLE_CL_OTHER, _('Other Liabilities')),

        (roles.ROLE_LTL_NOTES_PAYABLE, _('Notes Payable')),
        (roles.ROLE_LTL_BONDS_PAYABLE, _('Bonds Payable')),
        (roles.ROLE_LTL_MORTAGE_PAYABLE, _('Mortgage Payable')),

    )
     ),
    ('Equity', (
        # (roles.ROLE_PARENT_CAPITAL, _('Capital Account Parent')),

        (roles.ROLE_EQ_CAPITAL, _('Capital')),
        (roles.ROLE_EQ_COMMON_STOCK, _('Common Stock')),
        (roles.ROLE_EQ_PREFERRED_STOCK, _('Preferred Stock')),
        (roles.ROLE_EQ_ADJ, _('Other Equity Adjustments')),

        # (roles.ROLE_PARENT_INCOME, _('Income Account Parent')),
        (roles.ROLE_INCOME_SALES, _('Sales Income')),
        (roles.ROLE_INCOME_PASSIVE, _('Passive Income')),
        (roles.ROLE_INCOME_OTHER, _('Other Income')),

        # (roles.ROLE_PARENT_COGS, _('COGS Account Parent')),
        (roles.ROLE_COGS, _('Cost of Goods Sold')),

        # (roles.ROLE_PARENT_EXPENSE, _('Expense Account Parent')),
        # (roles.ROLE_EXPENSES, _('Expense')),
        (roles.ROLE_EXPENSES_OP, _('Operational Expense')),
        (roles.ROLE_EXPENSES_INTEREST, _('Interest Expense')),
        (roles.ROLE_EXPENSES_TAXES, _('Tax Expense')),
        (roles.ROLE_EXPENSES_CAPITAL, _('Capital Expense')),
        (roles.ROLE_EXPENSES_OTHER, _('Other Expense')),
    )
     )
]
ACCOUNT_CONVENTION = {
    'assets': 'debit',
    'liabilities': 'credit',
    'equity': 'credit'
}
ROLE_TUPLES = sum([[(r[0].lower(), s[0]) for s in r[1]] for r in ACCOUNT_ROLES], list())
ROLE_DICT = {
    t[0].lower(): [r[0] for r in t[1]] for t in ACCOUNT_ROLES
}
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

    def available(self, user):
        return self.for_user(user=user).filter(
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

    code = models.CharField(max_length=10, verbose_name=_l('Account Code'))
    name = models.CharField(max_length=100, verbose_name=_l('Account Name'))
    role = models.CharField(max_length=25, choices=ACCOUNT_ROLES, verbose_name=_l('Account Role'))
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
        abstract = True
        ordering = ['-created']
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
