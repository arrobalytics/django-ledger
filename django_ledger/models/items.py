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

from django_ledger.models.mixins import CreateUpdateMixIn, NodeTreeMixIn
from django_ledger.settings import DJANGO_LEDGER_CURRENCY_SYMBOL as currency_symbol

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

    def for_entity_active(self, entity_slug: str, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(is_active=True)


class UnitOfMeasureModelAbstract(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=50, verbose_name=_('Unit of Measure Name'))
    unit_abbr = models.SlugField(max_length=10, verbose_name=_('UoM Abbreviation'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
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


class UnitOfMeasureModel(UnitOfMeasureModelAbstract):
    """
    Base Unit of Measure Model from Abstract.
    """


class ItemModelMQuerySet(models.QuerySet):

    def active(self):
        return self.filter(active=True)


class ItemModelManager(models.Manager):

    def get_queryset(self):
        return ItemModelMQuerySet(self.model, using=self._db)

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

    def products_and_services(self, entity_slug: str, user_model):
        qs = self.for_entity_active(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(is_product_or_service=True)

    def expenses(self, entity_slug: str, user_model):
        qs = self.for_entity_active(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(
            is_product_or_service=False,
            for_inventory=False
        )

    def inventory(self, entity_slug: str, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(for_inventory=True)

    def for_bill(self, entity_slug: str, user_model):
        qs = self.for_entity_active(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(
            Q(is_product_or_service=False, for_inventory=False) |
            Q(for_inventory=True)
        )

    def for_po(self, entity_slug: str, user_model):
        qs = self.for_entity_active(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(
            Q(is_product_or_service=False, for_inventory=False) |
            Q(for_inventory=True)
        )


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
        verbose_name=_('Is an item for inventory'),
        help_text=_('It is an item you require for your inventory.'))

    is_product_or_service = models.BooleanField(
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
        help_text=_('Earnings account where revenue will be recognized on Income Statement.'),
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
                               related_name='items',
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
        if self.is_expense():
            return f'Expense Item: {self.name}'
        elif self.is_inventory():
            return f'Inventory: {self.name}'
        return f'Item Model: {self.name} - {self.sku}'

    def is_expense(self):
        return self.is_product_or_service is False and self.for_inventory is False

    def is_inventory(self):
        return self.for_inventory is True

    def clean(self):

        if all([
            self.for_inventory is False,
            self.is_product_or_service is False
        ]):
            if not self.expense_account:
                raise ValidationError(_('Items must have an associated expense accounts.'))
            self.inventory_account = None
            self.earnings_account = None
            self.cogs_account = None

        elif all([
            self.for_inventory is True,
            self.is_product_or_service is True
        ]):
            if not all([
                self.inventory_account,
                self.cogs_account,
                self.earnings_account
            ]):
                raise ValidationError(_('Items for resale must have Inventory, COGS & Earnings accounts.'))

        elif all([
            self.for_inventory is True,
            self.is_product_or_service is False
        ]):
            if not all([
                self.inventory_account,
                self.cogs_account
            ]):
                raise ValidationError(_('Items for inventory must have Inventory & COGS accounts.'))
            self.expense_account = None
            self.earnings_account = None

        elif all([
            self.for_inventory is False,
            self.is_product_or_service is True
        ]):
            if not self.earnings_account:
                raise ValidationError(_('Products & Services must have an Earnings Account'))
            self.expense_account = None
            self.inventory_account = None
            self.cogs_account = None


class ItemThroughModelQueryset(models.QuerySet):

    def is_received(self):
        return self.filter(po_item_status=ItemThroughModel.STATUS_RECEIVED)

    def in_transit(self):
        return self.filter(po_item_status=ItemThroughModel.STATUS_IN_TRANSIT)

    def is_ordered(self):
        return self.filter(po_item_status=ItemThroughModel.STATUS_ORDERED)


class ItemThroughModelManager(models.Manager):

    def get_queryset(self):
        return ItemThroughModelQueryset(self.model, using=self._db)

    def for_entity(self, user_model, entity_slug):
        qs = self.get_queryset()
        return qs.filter(
            Q(item_model__entity__slug__exact=entity_slug) &
            (
                    Q(item_model__entity__admin=user_model) |
                    Q(item_model__entity__managers__in=[user_model])
            )
        )

    def for_bill(self, user_model, entity_slug, bill_pk):
        qs = self.for_entity(user_model=user_model, entity_slug=entity_slug)
        return qs.filter(bill_model__uuid__exact=bill_pk)

    def for_invoice(self, entity_slug: str, invoice_pk, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(invoice_model__uuid__exact=invoice_pk)

    def for_po(self, entity_slug, user_model, po_pk):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(po_model__uuid__exact=po_pk)

    def inventory_all(self, entity_slug, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(item_model__for_inventory=True)

    def inventory_received(self, entity_slug, user_model):
        qs = self.inventory_all(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(po_item_status=ItemThroughModel.STATUS_RECEIVED)

    def is_orphan(self, entity_slug, user_model):
        # todo: implement is orphans...
        raise NotImplementedError


class ItemThroughModelAbstract(NodeTreeMixIn, CreateUpdateMixIn):
    STATUS_NOT_ORDERED = 'not_ordered'
    STATUS_ORDERED = 'ordered'
    STATUS_IN_TRANSIT = 'in_transit'
    STATUS_RECEIVED = 'received'
    STATUS_CANCELED = 'cancelled'

    PO_ITEM_STATUS = [
        (STATUS_NOT_ORDERED, _('Not Ordered')),
        (STATUS_ORDERED, _('Ordered')),
        (STATUS_IN_TRANSIT, _('In Transit')),
        (STATUS_RECEIVED, _('Received')),
        (STATUS_CANCELED, _('Canceled')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel',
                                    on_delete=models.SET_NULL,
                                    blank=True,
                                    null=True,
                                    verbose_name=_('Associated Entity Unit'))
    item_model = models.ForeignKey('django_ledger.ItemModel',
                                   on_delete=models.PROTECT,
                                   verbose_name=_('Item Model'))
    bill_model = models.ForeignKey('django_ledger.BillModel',
                                   on_delete=models.CASCADE,
                                   null=True,
                                   blank=True,
                                   verbose_name=_('Bill Model'))
    invoice_model = models.ForeignKey('django_ledger.InvoiceModel',
                                      on_delete=models.CASCADE,
                                      null=True, blank=True,
                                      verbose_name=_('Invoice Model'))
    po_model = models.ForeignKey('django_ledger.PurchaseOrderModel',
                                 on_delete=models.SET_NULL,
                                 null=True,
                                 blank=True,
                                 verbose_name=_('Purchase Order Model'))
    po_item_status = models.CharField(max_length=15,
                                      choices=PO_ITEM_STATUS,
                                      blank=True,
                                      null=True,
                                      verbose_name=_('PO Item Status'))

    quantity = models.FloatField(default=0.0,
                                 verbose_name=_('Quantity'),
                                 validators=[MinValueValidator(0)])
    unit_cost = models.FloatField(default=0.0,
                                  verbose_name=_('Cost Per Unit'),
                                  validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=20,
                                       editable=False,
                                       decimal_places=2,
                                       verbose_name=_('Total Amount QTY x UnitCost'),
                                       validators=[MinValueValidator(0)])
    objects = ItemThroughModelManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['bill_model', 'item_model']),
            models.Index(fields=['invoice_model', 'item_model']),
            models.Index(fields=['po_model', 'item_model']),
        ]

    def __str__(self):
        status_display = self.get_po_item_status_display()
        amount = f'{currency_symbol}{self.total_amount}'
        if self.po_model:
            return f'PO Through Model: {self.uuid} | {status_display} | {amount}'
        elif self.bill_model:
            return f'Bill Through Model: {self.uuid} | {status_display} | {amount}'
        elif self.invoice_model:
            return f'Invoice Through Model: {self.uuid} | {status_display} | {amount}'
        return f'Orphan Item Through Model: {self.uuid} | {status_display} | {amount}'

    def update_total_amount(self):
        self.total_amount = round(self.quantity * self.unit_cost, 2)

    def html_id(self):
        return f'djl-item-{self.uuid}'

    def html_id_unit_cost(self):
        return f'djl-item-unit-cost-id-{self.uuid}'

    def html_id_quantity(self):
        return f'djl-item-quantity-id-{self.uuid}'

    def is_cancelled(self):
        return self.po_item_status == self.STATUS_CANCELED

    def can_create_bill(self):
        return self.bill_model_id is None and self.po_item_status in [
            self.STATUS_ORDERED, self.STATUS_IN_TRANSIT, self.STATUS_RECEIVED
        ]

    def get_status_css_class(self):
        if self.po_item_status == self.STATUS_RECEIVED:
            return ' is-success'
        elif self.po_item_status == self.STATUS_CANCELED:
            return ' is-danger'
        elif self.po_item_status == self.STATUS_ORDERED:
            return ' is-info'
        return ' is-warning'

    def clean(self):
        self.update_total_amount()


class ItemThroughModel(ItemThroughModelAbstract):
    """
    Base Item Model Through Model for Many to Many Relationships
    """


class ItemModel(ItemModelAbstract):
    """
    Base Item Model from Abstract.
    """
