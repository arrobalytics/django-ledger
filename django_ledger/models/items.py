"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from decimal import Decimal
from string import ascii_lowercase, digits
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField, Value, Case, When
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import CreateUpdateMixIn, ParentChildMixIn
from django_ledger.settings import (DJANGO_LEDGER_CURRENCY_SYMBOL as currency_symbol,
                                    DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE)

ITEM_LIST_RANDOM_SLUG_SUFFIX = ascii_lowercase + digits


# UNIT OF MEASURES MODEL....
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


# ITEM MODEL....
class ItemModelQuerySet(models.QuerySet):

    def active(self):
        return self.filter(active=True)


class ItemModelManager(models.Manager):

    def get_queryset(self):
        return ItemModelQuerySet(self.model, using=self._db)

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__slug__exact=entity_slug) &
            (
                    Q(entity__managers__in=[user_model]) |
                    Q(entity__admin=user_model)
            )
        ).select_related('uom')

    def for_entity_active(self, entity_slug: str, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(is_active=True)

    def products_and_services(self, entity_slug: str, user_model):
        qs = self.for_entity_active(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(
            Q(is_product_or_service=True) &
            Q(for_inventory=False)
        )

    def expenses(self, entity_slug: str, user_model):
        qs = self.for_entity_active(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(
            is_product_or_service=False,
            for_inventory=False
        )

    def inventory(self, entity_slug: str, user_model):
        qs = self.for_entity_active(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(for_inventory=True)

    def for_bill(self, entity_slug: str, user_model):
        qs = self.for_entity_active(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(
            (
                    Q(is_product_or_service=False) &
                    Q(for_inventory=False)
            ) |
            Q(for_inventory=True)
        )

    def for_po(self, entity_slug: str, user_model):
        return self.inventory(entity_slug=entity_slug, user_model=user_model)

    def for_estimate(self, entity_slug: str, user_model):
        return self.products_and_services(entity_slug=entity_slug, user_model=user_model)

    def for_contract(self, entity_slug: str, user_model, ce_model_uuid):
        qs = self.for_estimate(
            entity_slug=entity_slug,
            user_model=user_model
        )
        qs = qs.filter(itemtransactionmodel__ce_model_id=ce_model_uuid)
        return qs.distinct('uuid')


class ItemModelAbstract(CreateUpdateMixIn):
    REL_NAME_PREFIX = 'item'

    LABOR_TYPE = 'L'
    MATERIAL_TYPE = 'M'
    EQUIPMENT_TYPE = 'E'
    LUMP_SUM = 'S'
    OTHER_TYPE = 'O'

    ITEM_CHOICES = [
        (LABOR_TYPE, _('Labor')),
        (MATERIAL_TYPE, _('Material')),
        (EQUIPMENT_TYPE, _('Equipment')),
        (LUMP_SUM, _('Lump Sum')),
        (OTHER_TYPE, _('Other')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=100, verbose_name=_('Item Name'))
    item_type = models.CharField(max_length=1, choices=ITEM_CHOICES, null=True, blank=True)

    uom = models.ForeignKey('django_ledger.UnitOfMeasureModel',
                            verbose_name=_('Unit of Measure'),
                            on_delete=models.RESTRICT)

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

    sold_as_unit = models.BooleanField(default=False)

    inventory_account = models.ForeignKey(
        'django_ledger.AccountModel',
        null=True,
        blank=True,
        verbose_name=_('Inventory Account'),
        related_name=f'{REL_NAME_PREFIX}_inventory_account',
        help_text=_('Inventory account where cost will be capitalized.'),
        on_delete=models.RESTRICT)
    inventory_received = models.DecimalField(
        null=True,
        blank=True,
        decimal_places=3,
        max_digits=20,
        verbose_name=_('Total inventory received.'))
    inventory_received_value = models.DecimalField(
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=20,
        verbose_name=_('Total value of inventory received.'))
    cogs_account = models.ForeignKey(
        'django_ledger.AccountModel',
        null=True,
        blank=True,
        verbose_name=_('COGS Account'),
        related_name=f'{REL_NAME_PREFIX}_cogs_account',
        help_text=_('COGS account where cost will be recognized on Income Statement.'),
        on_delete=models.RESTRICT)
    earnings_account = models.ForeignKey(
        'django_ledger.AccountModel',
        null=True,
        blank=True,
        verbose_name=_('Earnings Account'),
        related_name=f'{REL_NAME_PREFIX}_earnings_account',
        help_text=_('Earnings account where revenue will be recognized on Income Statement.'),
        on_delete=models.RESTRICT)
    expense_account = models.ForeignKey(
        'django_ledger.AccountModel',
        null=True,
        blank=True,
        verbose_name=_('Expense Account'),
        related_name=f'{REL_NAME_PREFIX}_expense_account',
        help_text=_('Expense account where cost will be recognized on Income Statement.'),
        on_delete=models.RESTRICT)

    additional_info = models.JSONField(blank=True,
                                       null=True,
                                       verbose_name=_('Item Additional Info'))
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
            models.Index(fields=['item_type']),
            models.Index(fields=['entity', 'sku']),
            models.Index(fields=['entity', 'upc']),
            models.Index(fields=['entity', 'item_id'])
        ]

    def __str__(self):
        if self.is_expense():
            return f'Expense Item: {self.name} | {self.get_item_type_display()}'
        elif self.is_inventory():
            return f'Inventory: {self.name} | {self.get_item_type_display()}'
        elif self.is_product_or_service:
            return f'Product/Service: {self.name} | {self.get_item_type_display()}'
        return f'Item Model: {self.name} - {self.sku} | {self.get_item_type_display()}'

    def is_expense(self):
        return self.is_product_or_service is False and self.for_inventory is False

    def is_inventory(self):
        return self.for_inventory is True

    def is_labor(self):
        return self.item_type == self.LABOR_TYPE

    def is_material(self):
        return self.item_type == self.MATERIAL_TYPE

    def is_equipment(self):
        return self.item_type == self.EQUIPMENT_TYPE

    def is_lump_sum(self):
        return self.item_type == self.LUMP_SUM

    def is_other(self):
        return self.item_type == self.OTHER_TYPE

    def get_average_cost(self) -> Decimal:
        if self.inventory_received:
            try:
                return self.inventory_received_value / self.inventory_received
            except ZeroDivisionError:
                pass
        return Decimal('0.00')

    def clean(self):

        if all([
            self.for_inventory is False,
            self.is_product_or_service is False
        ]):
            if not self.expense_account_id:
                raise ValidationError(_('Items must have an associated expense accounts.'))
            self.inventory_account = None
            self.earnings_account = None
            self.cogs_account = None

        elif all([
            self.for_inventory is True,
            self.is_product_or_service is True
        ]):
            if not all([
                self.inventory_account_id,
                self.cogs_account_id,
                self.earnings_account_id
            ]):
                raise ValidationError(_('Items for resale must have Inventory, COGS & Earnings accounts.'))

        elif all([
            self.for_inventory is True,
            self.is_product_or_service is False
        ]):
            if not all([
                self.inventory_account_id,
                self.cogs_account_id
            ]):
                raise ValidationError(_('Items for inventory must have Inventory & COGS accounts.'))
            self.expense_account = None
            self.earnings_account = None

        elif all([
            self.for_inventory is False,
            self.is_product_or_service is True
        ]):
            if not self.earnings_account_id:
                raise ValidationError(_('Products & Services must have an Earnings Account'))
            self.expense_account = None
            self.inventory_account = None
            self.cogs_account = None


# ITEM TRANSACTION MODELS...
class ItemTransactionModelQuerySet(models.QuerySet):

    def is_received(self):
        return self.filter(po_item_status=ItemTransactionModel.STATUS_RECEIVED)

    def in_transit(self):
        return self.filter(po_item_status=ItemTransactionModel.STATUS_IN_TRANSIT)

    def is_ordered(self):
        return self.filter(po_item_status=ItemTransactionModel.STATUS_ORDERED)


class ItemTransactionModelManager(models.Manager):

    def get_queryset(self):
        return ItemTransactionModelQuerySet(self.model, using=self._db)

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
        return qs.filter(bill_model_id__exact=bill_pk)

    def for_invoice(self, entity_slug: str, invoice_pk, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(invoice_model_id__exact=invoice_pk)

    def for_po(self, entity_slug, user_model, po_pk):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(po_model__uuid__exact=po_pk)

    def for_estimate(self, user_model, entity_slug, cj_pk):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return self.filter(ce_model_id__exact=cj_pk)

    def for_contract(self, user_model, entity_slug, ce_pk):
        """
        Returns all ItemTransactionModels associated with an EstimateModel.
        @param user_model: UserModel requesting data.
        @param entity_slug: EntityModel slug field value.
        @param ce_pk: EstimateModel UUID.
        @return: ItemTransactionModel QuerySet
        """
        qs = self.for_entity(
            entity_slug=entity_slug,
            user_model=user_model
        )
        return qs.filter(
            Q(ce_model_id__exact=ce_pk) |
            Q(po_model__ce_model_id__exact=ce_pk) |
            Q(bill_model__ce_model_id__exact=ce_pk) |
            Q(invoice_model__ce_model_id__exact=ce_pk)
        )

    def inventory_pipeline(self, entity_slug, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(
            Q(item_model__for_inventory=True) &
            Q(bill_model__isnull=False) &
            Q(po_item_status__in=[
                ItemTransactionModel.STATUS_ORDERED,
                ItemTransactionModel.STATUS_IN_TRANSIT,
                ItemTransactionModel.STATUS_RECEIVED,
            ])
        )

    def inventory_pipeline_aggregate(self, entity_slug: str, user_model):
        qs = self.inventory_pipeline(entity_slug=entity_slug, user_model=user_model)
        return qs.values(
            'item_model__name',
            'item_model__uom__name',
            'po_item_status').annotate(
            total_quantity=Sum('quantity'),
            total_value=Sum('total_amount')
        )

    def inventory_pipeline_ordered(self, entity_slug, user_model):
        qs = self.inventory_pipeline(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(po_item_status=ItemTransactionModel.STATUS_ORDERED)

    def inventory_pipeline_intransit(self, entity_slug, user_model):
        qs = self.inventory_pipeline(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(po_item_status=ItemTransactionModel.STATUS_IN_TRANSIT)

    def inventory_pipeline_received(self, entity_slug, user_model):
        qs = self.inventory_pipeline(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(po_item_status=ItemTransactionModel.STATUS_RECEIVED)

    def inventory_invoiced(self, entity_slug, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(
            Q(item_model__for_inventory=True) &
            Q(invoice_model__isnull=False)
        )

    def inventory_count(self, entity_slug, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        qs = qs.filter(
            Q(item_model__for_inventory=True) &
            (
                # received inventory...
                    (
                            Q(bill_model__isnull=False) &
                            Q(po_model__po_status='approved') &
                            Q(po_item_status__exact=ItemTransactionModel.STATUS_RECEIVED)
                    ) |

                    # invoiced inventory...
                    (
                        Q(invoice_model__isnull=False)
                    )

            )
        )

        return qs.values('item_model_id', 'item_model__name', 'item_model__uom__name').annotate(
            quantity_received=Coalesce(
                Sum('quantity', filter=Q(bill_model__isnull=False) & Q(invoice_model__isnull=True)), Value(0.0),
                output_field=DecimalField()),
            cost_received=Coalesce(
                Sum('total_amount', filter=Q(bill_model__isnull=False) & Q(invoice_model__isnull=True)), Value(0.0),
                output_field=DecimalField()),
            quantity_invoiced=Coalesce(
                Sum('quantity', filter=Q(invoice_model__isnull=False) & Q(bill_model__isnull=True)), Value(0.0),
                output_field=DecimalField()),
            revenue_invoiced=Coalesce(
                Sum('total_amount', filter=Q(invoice_model__isnull=False) & Q(bill_model__isnull=True)), Value(0.0),
                output_field=DecimalField()),
        ).annotate(
            quantity_onhand=Coalesce(F('quantity_received') - F('quantity_invoiced'), Value(0.0),
                                     output_field=DecimalField()),
            cost_average=Case(
                When(quantity_received__gt=0.0,
                     then=ExpressionWrapper(F('cost_received') / F('quantity_received'),
                                            output_field=DecimalField(decimal_places=3))
                     )
            ),
            value_onhand=Coalesce(
                ExpressionWrapper(F('quantity_onhand') * F('cost_average'),
                                  output_field=DecimalField(decimal_places=3)), Value(0.0), output_field=DecimalField())
        )

    def is_orphan(self, entity_slug, user_model):
        # todo: implement is orphans...
        raise NotImplementedError


class ItemTransactionModelAbstract(ParentChildMixIn, CreateUpdateMixIn):
    DECIMAL_PLACES = 2

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
    parent = models.ForeignKey('self',
                               null=True,
                               blank=True,
                               on_delete=models.RESTRICT,
                               related_name='children',
                               verbose_name=_('Parent Item'))
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel',
                                    on_delete=models.RESTRICT,
                                    blank=True,
                                    null=True,
                                    verbose_name=_('Associated Entity Unit'))
    item_model = models.ForeignKey('django_ledger.ItemModel',
                                   on_delete=models.RESTRICT,
                                   verbose_name=_('Item Model'))
    bill_model = models.ForeignKey('django_ledger.BillModel',
                                   on_delete=models.RESTRICT,
                                   null=True,
                                   blank=True,
                                   verbose_name=_('Bill Model'))
    invoice_model = models.ForeignKey('django_ledger.InvoiceModel',
                                      on_delete=models.RESTRICT,
                                      null=True,
                                      blank=True,
                                      verbose_name=_('Invoice Model'))

    # LEDGER TRANSACTION Fields (Bill/Invoice)....
    quantity = models.FloatField(null=True,
                                 blank=True,
                                 verbose_name=_('Quantity'),
                                 validators=[MinValueValidator(limit_value=0.0)])
    unit_cost = models.FloatField(null=True,
                                  blank=True,
                                  verbose_name=_('Cost Per Unit'),
                                  validators=[MinValueValidator(limit_value=0.0)])
    total_amount = models.DecimalField(max_digits=20,
                                       editable=False,
                                       null=True,
                                       blank=True,
                                       decimal_places=DECIMAL_PLACES,
                                       verbose_name=_('Total Amount QTY x UnitCost'),
                                       validators=[MinValueValidator(limit_value=0.0)])

    # Purchase Order fields...
    po_model = models.ForeignKey('django_ledger.PurchaseOrderModel',
                                 on_delete=models.RESTRICT,
                                 null=True,
                                 blank=True,
                                 verbose_name=_('Purchase Order Model'))
    po_quantity = models.FloatField(null=True,
                                    blank=True,
                                    verbose_name=_('PO Quantity'),
                                    help_text=_('Authorized item quantity for purchasing.'),
                                    validators=[MinValueValidator(limit_value=0.0)])
    po_unit_cost = models.FloatField(null=True,
                                     blank=True,
                                     verbose_name=_('PO Unit Cost'),
                                     help_text=_('Purchase Order unit cost.'),
                                     validators=[MinValueValidator(limit_value=0.0)])
    po_total_amount = models.DecimalField(max_digits=20,
                                          decimal_places=DECIMAL_PLACES,
                                          null=True,
                                          blank=True,
                                          editable=False,
                                          verbose_name=_('Authorized maximum item cost per Purchase Order'),
                                          help_text=_('Maximum authorized cost per Purchase Order.'),
                                          validators=[MinValueValidator(limit_value=0.0)])
    po_item_status = models.CharField(max_length=15,
                                      choices=PO_ITEM_STATUS,
                                      blank=True,
                                      null=True,
                                      verbose_name=_('PO Item Status'))

    # Estimate/Contract fields...
    ce_model = models.ForeignKey('django_ledger.EstimateModel',
                                 null=True,
                                 blank=True,
                                 verbose_name=_('Customer Estimate'),
                                 on_delete=models.RESTRICT)
    ce_quantity = models.FloatField(null=True,
                                    blank=True,
                                    verbose_name=_('Estimated/Contract Quantity'),
                                    validators=[MinValueValidator(limit_value=0.0)])
    ce_unit_cost_estimate = models.FloatField(null=True,
                                              blank=True,
                                              verbose_name=_('Estimate/Contract Cost per Unit.'),
                                              validators=[MinValueValidator(limit_value=0.0)])
    ce_cost_estimate = models.DecimalField(max_digits=20,
                                           null=True,
                                           blank=True,
                                           decimal_places=DECIMAL_PLACES,
                                           editable=False,
                                           verbose_name=_('Total Estimate/Contract Cost.'),
                                           validators=[MinValueValidator(limit_value=0.0)])
    ce_unit_revenue_estimate = models.FloatField(null=True,
                                                 blank=True,
                                                 verbose_name=_('Estimate/Contract Revenue per Unit.'),
                                                 validators=[MinValueValidator(limit_value=0.0)])
    ce_revenue_estimate = models.DecimalField(max_digits=20,
                                              null=True,
                                              blank=True,
                                              decimal_places=DECIMAL_PLACES,
                                              editable=False,
                                              verbose_name=_('Total Estimate/Contract Revenue.'),
                                              validators=[MinValueValidator(limit_value=0.0)])
    item_notes = models.CharField(max_length=400, null=True, blank=True, verbose_name=_('Description'))
    objects = ItemTransactionModelManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['bill_model', 'item_model']),
            models.Index(fields=['invoice_model', 'item_model']),
            models.Index(fields=['po_model', 'item_model']),
            models.Index(fields=['ce_model', 'item_model']),
            models.Index(fields=['po_item_status']),
            models.Index(fields=['parent'])
        ]

    def __str__(self):
        # pylint: disable=no-member

        # amount = f'{currency_symbol}{self.total_amount}'
        if self.po_model_id:
            po_status_display = self.get_po_item_status_display()
            return f'PO Model: {self.po_model_id} | {po_status_display} | {self.po_total_amount}'
        elif self.bill_model_id:
            return f'Bill Model: {self.bill_model_id} | {self.total_amount}'
        elif self.invoice_model_id:
            return f'Invoice Model: {self.invoice_model_id} | {self.total_amount}'
        elif self.ce_model_id:
            return f'Estimate/Contract Model: {self.ce_model_id} | {self.ce_cost_estimate}'
        return f'Orphan {self.__class__.__name__}: {self.uuid}'

    def is_received(self):
        return self.po_item_status == self.STATUS_RECEIVED

    def is_canceled(self):
        return self.po_item_status == self.STATUS_CANCELED

    # ItemTransactionModel Associations...
    def for_estimate(self) -> bool:
        """
        True if ItemTransactionModel is associated with an EstimateModel, else False.
        @return: True/False
        """
        return self.ce_model_id is not None

    def for_po(self):
        """
        True if ItemTransactionModel is associated with a PurchaseOrderModel, else False.
        @return:  True/False
        """
        return self.po_model_id is not None

    def for_invoice(self):
        """
        True if ItemTransactionModel is associated with an InvoiceModel, else False.
        @return:  True/False
        """
        return self.invoice_model_id is not None

    def for_bill(self):
        """
        True if ItemTransactionModel is associated with a BillModel, else False.
        @return:  True/False
        """
        return self.bill_model_id is not None

    # TRANSACTIONS...
    def update_total_amount(self):
        if any([
            self.for_bill(),
            self.for_invoice(),
            self.for_po()
        ]):
            if self.quantity is None:
                self.quantity = 0.0

            if self.unit_cost is None:
                self.unit_cost = 0.0

            self.total_amount = round(
                Decimal.from_float(self.quantity * self.unit_cost), self.DECIMAL_PLACES
            )

            if self.for_po():

                if self.quantity > self.po_quantity:
                    raise ValidationError(f'Billed quantity {self.quantity} cannot be greater than '
                                          f'PO quantity {self.po_quantity}')
                if self.total_amount > self.po_total_amount:
                    raise ValidationError(f'Item amount {self.total_amount} cannot exceed authorized '
                                          f'PO amount {self.po_total_amount}')

                if self.total_amount > self.po_total_amount:
                    # checks if difference is within tolerance...
                    diff = self.total_amount - self.po_total_amount
                    if diff > DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE:
                        raise ValidationError(
                            f'Difference between PO Amount {self.po_total_amount} and Bill {self.total_amount} '
                            f'exceeds tolerance of {DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE}')
                    self.total_amount = self.po_total_amount
                    return

    # PURCHASE ORDER...
    def update_po_total_amount(self):
        if self.for_po():
            if self.po_quantity is None:
                self.po_quantity = 0.0
            if self.po_unit_cost is None:
                self.po_unit_cost = 0.0

            self.po_total_amount = round(Decimal.from_float(self.po_quantity * self.po_unit_cost),
                                         self.DECIMAL_PLACES)

    # ESTIMATE/CONTRACTS...
    def update_cost_estimate(self):
        if self.for_estimate():
            if self.ce_quantity is None:
                self.ce_quantity = 0.00
            if self.ce_unit_cost_estimate is None:
                self.ce_unit_cost_estimate = 0.00
            self.ce_cost_estimate = round(Decimal.from_float(self.ce_quantity * self.ce_unit_cost_estimate),
                                          self.DECIMAL_PLACES)

    def update_revenue_estimate(self):
        if self.for_estimate():
            if self.ce_quantity is None:
                self.ce_quantity = 0.00
            if self.ce_unit_revenue_estimate is None:
                self.ce_unit_revenue_estimate = 0.00
            self.ce_revenue_estimate = Decimal.from_float(self.ce_quantity * self.ce_unit_revenue_estimate)

    # HTML TAGS...
    def html_id(self):
        return f'djl-item-{self.uuid}'

    def html_id_unit_cost(self):
        return f'djl-item-unit-cost-id-{self.uuid}'

    def html_id_quantity(self):
        return f'djl-item-quantity-id-{self.uuid}'

    def is_cancelled(self):
        return self.po_item_status == self.STATUS_CANCELED

    def can_create_bill(self):
        # pylint: disable=no-member
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

        self.update_po_total_amount()
        self.update_cost_estimate()
        self.update_revenue_estimate()

        self.update_total_amount()


# FINAL MODEL CLASSES....

class UnitOfMeasureModel(UnitOfMeasureModelAbstract):
    """
    Base Unit of Measure Model from Abstract.
    """


class ItemTransactionModel(ItemTransactionModelAbstract):
    """
    Base Item Transaction Model.
    """


class ItemModel(ItemModelAbstract):
    """
    Base Item Model from Abstract.
    """
