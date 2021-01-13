"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from string import ascii_lowercase, digits
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import CreateUpdateMixIn

ITEM_LIST_RANDOM_SLUG_SUFFIX = ascii_lowercase + digits


class UnitOfMeasureModelManager(models.Manager):

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__slug__exact=entity_slug) &
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
        )


class UnitOfMeasureModelAbstract(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=50, verbose_name=_('Unit of Measure Name'))
    unit_abbr = models.SlugField(max_length=10, verbose_name=_('UoM Abbreviation'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('UoM Entity'))

    objects = UnitOfMeasureModelManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['entity'])
        ]
        unique_together = [
            ('entity', 'unit_abbr')
        ]

    def __str__(self):
        return f'{self.name} ({self.unit_abbr})'


class ItemModelManager(models.Manager):

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__slug__exact=entity_slug) &
            (
                    Q(entity__managers__in=[user_model]) |
                    Q(entity__admin=user_model)
            )
        )

    def for_entity_active(self, entity_slug: str, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(is_active=True)


class ItemModelAbstract(CreateUpdateMixIn):
    REL_NAME_PREFIX = 'item'

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=100, verbose_name=_('Item Name'))

    uom = models.ForeignKey('django_ledger.UnitOfMeasureModel',
                            verbose_name=_('Unit of Measure'),
                            on_delete=models.PROTECT)

    sku = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('SKU Code'))
    upc = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('UPC Code'))
    item_id = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Internal ID'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    default_amount = models.DecimalField(max_digits=20,
                                         decimal_places=2,
                                         default=0,
                                         verbose_name=_('Default monetary value per unit of measure'),
                                         validators=[MinValueValidator(0)])

    for_inventory = models.BooleanField(
        default=False,
        verbose_name=_('Is an item for inventory'),
        help_text=_('It is an item you require for your inventory.'))

    is_product_or_service = models.BooleanField(
        default=False,
        verbose_name=_('Is a product or service.'),
        help_text=_('Is a product or service you sell or provide to customers.'))

    inventory_account = models.ForeignKey(
        'django_ledger.AccountModel',
        null=True,
        blank=True,
        verbose_name=_('Inventory Account'),
        related_name=f'{REL_NAME_PREFIX}_inventory_account',
        help_text=_('Inventory account where cost will be capitalized.'),
        on_delete=models.PROTECT)
    cogs_account = models.ForeignKey(
        'django_ledger.AccountModel',
        null=True,
        blank=True,
        verbose_name=_('COGS Account'),
        related_name=f'{REL_NAME_PREFIX}_cogs_account',
        help_text=_('COGS account where cost will be recognized on Income Statement.'),
        on_delete=models.PROTECT)
    earnings_account = models.ForeignKey(
        'django_ledger.AccountModel',
        null=True,
        blank=True,
        verbose_name=_('Earnings Account'),
        related_name=f'{REL_NAME_PREFIX}_earnings_account',
        help_text=_('COGS account where revenue will be recognized on Income Statement.'),
        on_delete=models.PROTECT)
    expense_account = models.ForeignKey(
        'django_ledger.AccountModel',
        null=True,
        blank=True,
        verbose_name=_('Expense Account'),
        related_name=f'{REL_NAME_PREFIX}_expense_account',
        help_text=_('Expense account where cost will be recognized on Income Statement.'),
        on_delete=models.PROTECT)

    additional_info = models.JSONField(default=dict, verbose_name=_('Item Additional Info'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('Item Entity'))

    objects = ItemModelManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['inventory_account']),
            models.Index(fields=['cogs_account']),
            models.Index(fields=['earnings_account']),
            models.Index(fields=['expense_account']),
            models.Index(fields=['for_inventory']),
            models.Index(fields=['is_product_or_service']),
            models.Index(fields=['is_active']),
            models.Index(fields=['entity', 'sku']),
            models.Index(fields=['entity', 'upc']),
            models.Index(fields=['entity', 'item_id']),
        ]

    def __str__(self):
        return f'Item Model: {self.name} - {self.sku}'

    def clean(self):
        if any([
            self.for_inventory,
            self.is_product_or_service
        ]):
            if self.for_inventory:
                if not all([
                    self.inventory_account,
                    self.cogs_account
                ]):
                    raise ValidationError(_('Items for inventory must have Inventory & COGS accounts'))
                self.expense_account = None
                self.earnings_account = None
            if self.is_product_or_service:
                if not self.earnings_account:
                    raise ValidationError(_('Products & Services must have an Earning Account'))
                self.expense_account = None
                self.inventory_account = None
                self.cogs_account = None

        else:
            if not self.expense_account:
                raise ValidationError(_('Items must have an associated expense accounts.'))
            self.inventory_account = None
            self.earnings_account = None
            self.cogs_account = None


class UnitOfMeasureModel(UnitOfMeasureModelAbstract):
    """
    Base Unit of Measure Model from Abstract.
    """


class ItemModel(ItemModelAbstract):
    """
    Base Item Model from Abstract.
    """
