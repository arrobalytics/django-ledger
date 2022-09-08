"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal
from random import choices
from string import ascii_lowercase, digits
from typing import Tuple, Union
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from treebeard.mp_tree import MP_Node, MP_NodeManager

from django_ledger.io import IOMixIn
from django_ledger.io.roles import ASSET_CA_CASH, EQUITY_CAPITAL, EQUITY_COMMON_STOCK, EQUITY_PREFERRED_STOCK
from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn, ContactInfoMixIn
from django_ledger.models.utils import LazyLoader

UserModel = get_user_model()
lazy_loader = LazyLoader()

ENTITY_RANDOM_SLUG_SUFFIX = ascii_lowercase + digits


def inventory_adjustment(counted_qs, recorded_qs) -> defaultdict:
    counted_map = {
        (i['item_model_id'], i['item_model__name'], i['item_model__uom__name']): {
            'count': i['quantity_onhand'],
            'value': i['value_onhand'],
            'avg_cost': i['cost_average']
            if i['quantity_onhand'] else Decimal('0.00')
        } for i in counted_qs
    }
    recorded_map = {
        (i['uuid'], i['name'], i['uom__name']): {
            'count': i['inventory_received'] or Decimal.from_float(0.0),
            'value': i['inventory_received_value'] or Decimal.from_float(0.0),
            'avg_cost': i['inventory_received_value'] / i['inventory_received']
            if i['inventory_received'] else Decimal('0.00')
        } for i in recorded_qs
    }

    # todo: change this to use a groupby then sum...
    item_ids = list(set(list(counted_map.keys()) + list(recorded_map)))
    adjustment = defaultdict(lambda: {
        # keeps track of inventory recounts...
        'counted': Decimal('0.000'),
        'counted_value': Decimal('0.00'),
        'counted_avg_cost': Decimal('0.00'),

        # keeps track of inventory level...
        'recorded': Decimal('0.000'),
        'recorded_value': Decimal('0.00'),
        'recorded_avg_cost': Decimal('0.00'),

        # keeps track of necessary inventory adjustment...
        'count_diff': Decimal('0.000'),
        'value_diff': Decimal('0.00'),
        'avg_cost_diff': Decimal('0.00')
    })

    for uid in item_ids:

        count_data = counted_map.get(uid)
        if count_data:
            avg_cost = count_data['value'] / count_data['count'] if count_data['count'] else Decimal('0.000')

            adjustment[uid]['counted'] = count_data['count']
            adjustment[uid]['counted_value'] = count_data['value']
            adjustment[uid]['counted_avg_cost'] = avg_cost

            adjustment[uid]['count_diff'] += count_data['count']
            adjustment[uid]['value_diff'] += count_data['value']
            adjustment[uid]['avg_cost_diff'] += avg_cost

        recorded_data = recorded_map.get(uid)
        if recorded_data:
            counted = recorded_data['count']
            avg_cost = recorded_data['value'] / counted if recorded_data['count'] else Decimal('0.000')

            adjustment[uid]['recorded'] = counted
            adjustment[uid]['recorded_value'] = recorded_data['value']
            adjustment[uid]['recorded_avg_cost'] = avg_cost

            adjustment[uid]['count_diff'] -= counted
            adjustment[uid]['value_diff'] -= recorded_data['value']
            adjustment[uid]['avg_cost_diff'] -= avg_cost

    return adjustment


def generate_entity_slug(name: str) -> str:
    slug = slugify(name)
    suffix = ''.join(choices(ENTITY_RANDOM_SLUG_SUFFIX, k=8))
    entity_slug = f'{slug}-{suffix}'
    return entity_slug


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


class EntityModelManager(MP_NodeManager):

    def for_user(self, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(admin=user_model) |
            Q(managers__in=[user_model])
        )


class EntityModelAbstract(MP_Node,
                          SlugNameMixIn,
                          CreateUpdateMixIn,
                          ContactInfoMixIn,
                          IOMixIn,
                          EntityReportManager):
    CASH_METHOD = 'cash'
    ACCRUAL_METHOD = 'accrual'
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
    managers = models.ManyToManyField(UserModel,
                                      through='EntityManagementModel',
                                      related_name='managed_by',
                                      verbose_name=_('Managers'))

    hidden = models.BooleanField(default=False)
    accrual_method = models.BooleanField(default=False,
                                         verbose_name=_('Use Accrual Method'))
    fy_start_month = models.IntegerField(choices=FY_MONTHS, default=1, verbose_name=_('Fiscal Year Start'))
    picture = models.ImageField(blank=True, null=True)
    objects = EntityModelManager()

    node_order_by = ['uuid']

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Entity')
        verbose_name_plural = _('Entities')
        indexes = [
            models.Index(fields=['admin'])
        ]

    def __str__(self):
        return f'{self.name}'

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

    def generate_slug(self, force_update: bool = False):
        if not force_update and self.slug:
            raise ValidationError(
                message=_(f'Cannot replace existing slug {self.slug}. Use force_update=True if needed.')
            )
        self.slug = generate_entity_slug(self.name)

    def recorded_inventory(self, user_model, queryset=None, as_values=True):
        if not queryset:
            # pylint: disable=no-member
            recorded_qs = self.items.inventory(
                entity_slug=self.slug,
                user_model=user_model
            )
        else:
            recorded_qs = queryset
        if as_values:
            return recorded_qs.values(
                'uuid', 'name', 'uom__name', 'inventory_received', 'inventory_received_value')
        return recorded_qs

    def update_inventory(self, user_model, commit: bool = False):

        ItemThroughModel = lazy_loader.get_item_transaction_model()
        ItemModel = lazy_loader.get_item_model()

        counted_qs = ItemThroughModel.objects.inventory_count(
            entity_slug=self.slug,
            user_model=user_model
        )
        recorded_qs = self.recorded_inventory(user_model=user_model, as_values=False)
        recorded_qs_values = self.recorded_inventory(
            user_model=user_model,
            queryset=recorded_qs,
            as_values=True)

        adj = inventory_adjustment(counted_qs, recorded_qs_values)

        updated_items = list()
        for (uuid, name, uom), i in adj.items():
            item_model: ItemModel = recorded_qs.get(uuid__exact=uuid)
            item_model.inventory_received = i['counted']
            item_model.inventory_received_value = i['counted_value']
            item_model.clean()
            updated_items.append(item_model)

        if commit:
            ItemModel.objects.bulk_update(updated_items,
                                          fields=[
                                              'inventory_received',
                                              'inventory_received_value',
                                              'updated'
                                          ])

        return adj, counted_qs, recorded_qs

    def populate_default_coa(self, activate_accounts: bool = False):
        # pylint: disable=no-member
        coa: ChartOfAccountModel = self.coa
        has_accounts = coa.accounts.all().exists()
        if not has_accounts:
            acc_objs = [
                AccountModel(
                    code=a['code'],
                    name=a['name'],
                    role=a['role'],
                    balance_type=a['balance_type'],
                    active=activate_accounts,
                    coa=coa,
                ) for a in CHART_OF_ACCOUNTS
            ]

            for acc in acc_objs:
                acc.clean()
            AccountModel.on_coa.bulk_create(acc_objs)

    def get_accounts(self, user_model, active_only: bool = True):
        """
        This func does...
        @param user_model: Request User Model
        @param active_only: Active accounts only
        @return: A queryset.
        """
        accounts_qs = AccountModel.on_coa.for_entity(
            entity_slug=self.slug,
            user_model=user_model
        )
        if active_only:
            accounts_qs = accounts_qs.active()
        return accounts_qs

    def add_equity(self,
                   user_model,
                   cash_account: Union[str, AccountModel],
                   equity_account: Union[str, AccountModel],
                   txs_date: Union[date, str],
                   amount: Decimal,
                   ledger_name: str,
                   ledger_posted: bool = False,
                   je_posted: bool = False):

        if not isinstance(cash_account, AccountModel) and not isinstance(equity_account, AccountModel):

            account_qs = AccountModel.on_coa.with_roles(
                roles=[
                    EQUITY_CAPITAL,
                    EQUITY_COMMON_STOCK,
                    EQUITY_PREFERRED_STOCK,
                    ASSET_CA_CASH
                ],
                entity_slug=self.slug,
                user_model=user_model
            )

            cash_account_model = account_qs.get(code__exact=cash_account)
            equity_account_model = account_qs.get(code__exact=equity_account)

        elif isinstance(cash_account, AccountModel) and isinstance(equity_account, AccountModel):
            cash_account_model = cash_account
            equity_account_model = equity_account

        else:
            raise ValidationError(
                message=f'Both cash_account and equity account must be an instance of str or AccountMode.'
                        f' Got. Cash Account: {cash_account.__class__.__name__} and '
                        f'Equity Account: {equity_account.__class__.__name__}'
            )

        txs = list()
        txs.append({
            'account_id': cash_account_model.uuid,
            'tx_type': 'debit',
            'amount': amount,
            'description': f'Sample data for {self.name}'
        })
        txs.append({
            'account_id': equity_account_model.uuid,
            'tx_type': 'credit',
            'amount': amount,
            'description': f'Sample data for {self.name}'
        })

        # pylint: disable=no-member
        ledger = self.ledgermodel_set.create(
            name=ledger_name,
            posted=ledger_posted
        )

        # todo: this needs to be changes to use the JournalEntryModel API for validation...
        self.commit_txs(
            je_date=txs_date,
            je_txs=txs,
            je_activity=JournalEntryModel.INVESTING_ACTIVITY,
            je_posted=je_posted,
            je_ledger=ledger
        )
        return ledger

    def is_cash_method(self) -> bool:
        return self.accrual_method is False

    def is_accrual_method(self) -> bool:
        return self.accrual_method is True

    def get_accrual_method(self) -> str:
        if self.is_cash_method():
            return self.CASH_METHOD
        return self.ACCRUAL_METHOD

    def clean(self):
        super(EntityModelAbstract, self).clean()
        if not self.name:
            raise ValidationError(message=_('Must provide a name for EntityModel'))

        if not self.slug:
            self.generate_slug()


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


def entitymodel_presave(instance: EntityModel, **kwargs):
    if not instance.slug:
        instance.slug = instance.generate_slug()


pre_save.connect(entitymodel_presave, EntityModel)


def entitymodel_postsave(instance: EntityModel, **kwargs):
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
