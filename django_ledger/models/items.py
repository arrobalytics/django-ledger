"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

The Items refer to the additional detail provided to Bills, Invoices, Purchase Orders and Estimates for the purposes of
documenting a breakdown of materials, labor, equipment, and other resources used for the purposes of the business
operations.

The items associated with any of the aforementioned models are responsible for calculating the different amounts
that ultimately drive the behavior of Journal Entries onto the company books.

Each item must be assigned a UnitOfMeasureModel which is the way or method used to quantify such resource. Examples
are Pounds, Gallons, Man Hours, etc used to measure how resources are quantified when associated with a specific
ItemTransactionModel. If many unit of measures are used for the same item, it would constitute a different item hence a
new record must be created.

ItemsTransactionModels constitute the way multiple items and used resources are associated with Bills, Invoices,
Purchase Orders and Estimates. Each transaction will record the unit of measure and quantity of each resource.
Totals will be calculated and associated with the containing model at the time of update.
"""
import warnings
from decimal import Decimal
from string import ascii_lowercase, digits
from typing import Dict
from uuid import uuid4, UUID

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField, Value, Case, When, QuerySet, Manager
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _

from django_ledger.models.deprecations import deprecated_entity_slug_behavior
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import (
    DJANGO_LEDGER_TRANSACTION_MAX_TOLERANCE, DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
    DJANGO_LEDGER_EXPENSE_NUMBER_PREFIX, DJANGO_LEDGER_INVENTORY_NUMBER_PREFIX,
    DJANGO_LEDGER_PRODUCT_NUMBER_PREFIX, DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR
)

ITEM_LIST_RANDOM_SLUG_SUFFIX = ascii_lowercase + digits


class ItemModelValidationError(ValidationError):
    pass


class UnitOfMeasureModelQuerySet(QuerySet):

    def for_user(self, user_model) -> 'UnitOfMeasureModelQuerySet':
        return self.filter(
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
        )


# UNIT OF MEASURES MODEL....
class UnitOfMeasureModelManager(Manager):
    """
    A custom-defined QuerySet Manager for the UnitOfMeasureModel.
    """

    def get_queryset(self) -> UnitOfMeasureModelQuerySet:
        return UnitOfMeasureModelQuerySet(self.model, using=self._db)

    @deprecated_entity_slug_behavior
    def for_entity(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs) -> UnitOfMeasureModelQuerySet:
        """
        Fetches the UnitOfMeasureModels associated with the provided EntityModel and UserModel.

        Parameters
        ----------
        entity_model: str or EntityModel
            The EntityModel slug or EntityModel used to filter the QuerySet.

        Returns
        -------
        QuerySet
            A QuerySet with applied filters.
        """

        EntityModel = lazy_loader.get_entity_model()
        qs = self.get_queryset()

        if 'user_model' in kwargs:
            warnings.warn(
                'user_model parameter is deprecated and will be removed in a future release. '
                'Use for_user(user_model).for_entity(entity_model) instead to keep current behavior.',
                DeprecationWarning,
                stacklevel=2
            )
            if DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR:
                qs = qs.for_user(kwargs['user_model'])

        if isinstance(entity_model, EntityModel):
            qs = qs.filter(entity=entity_model)
        elif isinstance(entity_model, str):
            qs = qs.filter(entity__slug=entity_model)
        elif isinstance(entity_model, UUID):
            qs = qs.filter(entity_id=entity_model)
        else:
            raise ItemModelValidationError(
                message='Must pass EntityModel, slug or UUID'
            )
        return qs

    @deprecated_entity_slug_behavior
    def for_entity_active(
            self, entity_model: 'EntityModel | str | UUID' = None,
            **kwargs) -> UnitOfMeasureModelQuerySet:
        """
        Fetches the Active UnitOfMeasureModels associated with the provided EntityModel and UserModel.

        Parameters
        ----------
        entity_model: str or EntityModel
            The EntityModel slug or EntityModel used to filter the QuerySet.
        Returns
        -------
        QuerySet
            A QuerySet with applied filters.
        """
        qs = self.for_entity(entity_model=entity_model, **kwargs)
        return qs.filter(is_active=True)


class UnitOfMeasureModelAbstract(CreateUpdateMixIn):
    """
    Base implementation of a Unit of Measure assigned to each Item Transaction.

    Attributes
    ----------
    uuid: UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().
    name: str
        The name of the unit of measure. Maximum of 50 characters.
    unit_abbr: str
        An abbreviation of the unit of measure used as an identifier or slug for URLs and queries.
    is_active: bool
        A boolean representing of the UnitOfMeasureModel instance is active to be used on new transactions.
    entity: EntityModel
        The EntityModel associated with the UnitOfMeasureModel instance.
    """
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=50, verbose_name=_('Unit of Measure Name'))
    unit_abbr = models.SlugField(max_length=10, verbose_name=_('UoM Abbreviation'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    # todo: rename to entity_model
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('UoM Entity'))

    objects = UnitOfMeasureModelManager.from_queryset(queryset_class=UnitOfMeasureModelQuerySet)()

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
class ItemModelQuerySet(QuerySet):
    """
    A custom-defined ItemModelQuerySet that implements custom QuerySet methods related to the ItemModel.
    """

    def for_user(self, user_model) -> 'ItemModelQuerySet':
        if user_model.is_superuser:
            return self
        return self.filter(
            Q(entity__managers__in=[user_model]) |
            Q(entity__admin=user_model)
        )

    def active(self):
        """
        Filters the QuerySet to only active Item Models.

        Returns
        -------
        ItemModelQuerySet
            A QuerySet with applied filters.
        """
        return self.filter(is_active=True)

    def products(self) -> 'ItemModelQuerySet':
        """
        Filters the QuerySet to ItemModels that only qualify as products.

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        return self.filter(
            (
                    Q(is_product_or_service=True) &
                    Q(for_inventory=True)
            ) |
            Q(item_role=ItemModel.ITEM_ROLE_PRODUCT)
        )

    def services(self) -> 'ItemModelQuerySet':
        """
        Filters the QuerySet to ItemModels that only qualify as services.

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        return self.filter(
            (
                    Q(is_product_or_service=True) &
                    Q(for_inventory=False)
            ) |
            Q(item_role=ItemModel.ITEM_ROLE_SERVICE)
        )

    def expenses(self) -> 'ItemModelQuerySet':
        """
        Filters the QuerySet to ItemModels that only qualify as expenses.

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        return self.filter(
            (
                    Q(is_product_or_service=False) &
                    Q(for_inventory=False)
            ) | Q(item_role=ItemModel.ITEM_ROLE_EXPENSE)
        )

    def inventory_wip(self) -> 'ItemModelQuerySet':
        """
        Filters the QuerySet to ItemModels that only qualify as inventory.
        These types of items cannot be sold as they are not considered a finished product.

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        return self.filter(
            (
                    Q(is_product_or_service=False) &
                    Q(for_inventory=True)
            ) | Q(item_role=ItemModel.ITEM_ROLE_INVENTORY)
        )

    def inventory_all(self) -> 'ItemModelQuerySet':
        """
        Filters the QuerySet to ItemModels that only qualify as inventory.
        These types of items may be finished or unfinished.


        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        return self.filter(
            (
                    (
                            Q(is_product_or_service=False) &
                            Q(for_inventory=True)
                    ) | Q(item_role=ItemModel.ITEM_ROLE_INVENTORY)
            ) |
            (
                    (
                            Q(is_product_or_service=True) &
                            Q(for_inventory=True)
                    ) |
                    Q(item_role=ItemModel.ITEM_ROLE_PRODUCT)

            )
        )

    def bills(self) -> 'ItemModelQuerySet':
        """
        Filters the QuerySet to ItemModels that are eligible only for bills..

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        return self.filter(
            (
                    Q(is_product_or_service=False) &
                    Q(for_inventory=False)
            ) |
            Q(for_inventory=True)
        )

    def invoices(self) -> 'ItemModelQuerySet':
        return self.filter(is_product_or_service=True)

    def estimates(self) -> 'ItemModelQuerySet':
        return self.invoices()

    def purchase_orders(self) -> 'ItemModelQuerySet':
        return self.inventory_all()


class ItemModelManager(Manager):
    """
    A custom defined ItemModelManager that implement custom QuerySet methods related to the ItemModel
    """

    def get_queryset(self) -> ItemModelQuerySet:
        return ItemModelQuerySet(self.model, using=self._db).select_related('uom')

    @deprecated_entity_slug_behavior
    def for_entity(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs) -> ItemModelQuerySet:
        """
        Marks the `for_entity` method as deprecated in behavior and provides an updated usage approach.

        This method allows querying a `QuerySet` filtered by various representations of an entity, such as an
        instance of `EntityModel`, a string slug, or a UUID. Leveraging this method with deprecated parameters
        may lead to a warning and compatibility concerns in future releases.

        Parameters
        ----------
        entity_model : EntityModel | str | UUID, optional
            The entity to filter the queryset by. Can be an instance of `EntityModel`, a slug (`str`), or
            a unique identifier (`UUID`). If not provided, no filtering is applied.
        kwargs : dict
            Additional keyword arguments, though currently only the `user_model` parameter is recognized but
            deprecated. The `user_model` behavior will be removed in future releases.

        Returns
        -------
        ItemModelQuerySet
            A filtered queryset corresponding to the specified entity.

        Raises
        ------
        ItemModelValidationError
            If the `entity_model` parameter is not of type `EntityModel`, `str`, or `UUID`.
        DeprecationWarning
            When the `user_model` parameter is used, indicating behavior slated for future removal.
        """
        EntityModel = lazy_loader.get_entity_model()
        qs = self.get_queryset()
        if 'user_model' in kwargs:
            warnings.warn(
                'user_model parameter is deprecated and will be removed in a future release. '
                'Use for_user(user_model).for_entity(entity_model) instead to keep current behavior.',
                DeprecationWarning,
                stacklevel=2
            )
            if DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR:
                qs = qs.for_user(kwargs['user_model'])

        if isinstance(entity_model, EntityModel):
            qs = qs.filter(entity=entity_model)
        elif isinstance(entity_model, str):
            qs = qs.filter(entity__slug__exact=entity_model)
        elif isinstance(entity_model, UUID):
            qs = qs.filter(entity_id=entity_model)
        else:
            raise ItemModelValidationError(
                message='entity_model parameter must be of type str or EntityModel or UUID'
            )
        return qs

    @deprecated_entity_slug_behavior
    def for_entity_active(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs) -> ItemModelQuerySet:
        """
        Returns a QuerySet of Active ItemModel associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        ----------
        entity_model: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        qs = self.for_entity(
            entity_model=entity_model,
            **kwargs
        )
        return qs.filter(is_active=True)

    @deprecated_entity_slug_behavior
    def for_invoice(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs) -> ItemModelQuerySet:
        """
        Returns a QuerySet of ItemModels that can only be used for InvoiceModels for a specific EntityModel &
        UserModel. These types of items qualify as products or services sold.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        ----------
        entity_model: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        qs = self.for_entity_active(entity_model=entity_model, **kwargs)
        return qs.filter(is_product_or_service=True)

    @deprecated_entity_slug_behavior
    def for_bill(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs) -> ItemModelQuerySet:
        """
        Returns a QuerySet of ItemModels that can only be used for BillModels for a specific EntityModel &
        UserModel. These types of items qualify as expenses or inventory purchases.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        ----------
        entity_model: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        qs = self.for_entity_active(
            entity_model=entity_model,
            **kwargs
        )
        return qs.filter(
            (
                    Q(is_product_or_service=False) &
                    Q(for_inventory=False)
            ) |
            Q(for_inventory=True)
        )

    @deprecated_entity_slug_behavior
    def for_po(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs) -> ItemModelQuerySet:
        """
        Returns a QuerySet of ItemModels that can only be used for PurchaseOrders for a specific EntityModel &
        UserModel. These types of items qualify as inventory purchases.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        ----------
        entity_model: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        qs = self.for_entity(entity_model=entity_model, **kwargs)
        return qs.inventory_all()

    @deprecated_entity_slug_behavior
    def for_estimate(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs) -> ItemModelQuerySet:
        """
        Returns a QuerySet of ItemModels that can only be used for EstimateModels for a specific EntityModel &
        UserModel. These types of items qualify as products.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        ----------
        entity_model: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.

        Returns
        -------
        ItemModelQuerySet
            A Filtered ItemModelQuerySet.
        """
        qs = self.for_entity_active(entity_model=entity_model, **kwargs)
        return qs.products()


class ItemModelAbstract(CreateUpdateMixIn):
    """
    Base implementation of the ItemModel.

    Attributes
    ----------
    uuid: UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().
    name: str
        Human readable name of the ItemModel instance. Maximum of 100 characters.
    item_role: str
        A choice of ITEM_ROLE_CHOICES that determines whether the ItemModel should be treated as an expense, inventory,
        service or product.
    item_type: str
        A choice of ITEM_TYPE_CHOICES that determines whether the ItemModel should be treated as labor, material,
        equipment, lump sum or other.
    uom: UnitOfMeasureModel
        The assigned UnitOfMeasureModel of the ItemModel instance. Mandatory.
    sku: str
        The SKU number associated with the ItemModel instance. Maximum 50 characters.
    upc: str
        The UPC number associated with the ItemModel instance. Maximum 50 characters.
    item_id: str
        EntityModel specific id associated with the ItemModel instance. Maximum 50 characters.
    item_number: str
        Auto generated human-readable item number.
    is_active: bool
        Determines if the ItemModel instance is considered active. Defaults to True.
    default_amount: Decimal
        The default, prepopulated monetary amount of the ItemModel instance .
    for_inventory: bool
        Legacy field used to determine if the ItemModel instance is considered an inventory item. Mandatory.
        Superseded by item_role field. Will be deprecated.
    is_product_or_service: bool
        Legacy field used to determine if the ItemModel instance is considered a product or service item. Mandatory.
        Superseded by item_role field. Will be deprecated.
    sold_as_unit: bool
        Determines if only whole numbers can be used when specifying the quantity on ItemTransactionModels.
    inventory_account: AccountModel
        Inventory account associated with the ItemModel instance. Enforced if ItemModel instance is_inventory() is True.
    inventory_received: Decimal
        Holds the total quantity of the inventory received for the whole EntityModel instance.
    inventory_received_value: Decimal
        Holds the total monetary value of the inventory received for the whole EntityModel instance.
    cogs_account: AccountModel
        COGS account associated with the ItemModel instance. Enforced if ItemModel instance is_inventory() is True.
    earnings_account: AccountModel
        Earnings account associated with the ItemModel instance. Enforced if ItemModel instance is_product() or
         is_service() is True.
    expense_account: AccountModel
        Expense account associated with the ItemModel instance. Enforced if ItemModel instance is_expense() is True.
    additional_info: dict
        Additional user defined information stored as JSON document in the Database.
    entity: EntityModel
        The EntityModel associated with the ItemModel instance.
    """
    REL_NAME_PREFIX = 'item'

    ITEM_TYPE_LABOR = 'L'
    ITEM_TYPE_MATERIAL = 'M'
    ITEM_TYPE_EQUIPMENT = 'E'
    ITEM_TYPE_LUMP_SUM = 'S'
    ITEM_TYPE_OTHER = 'O'
    ITEM_TYPE_CHOICES = [
        (ITEM_TYPE_LABOR, _('Labor')),
        (ITEM_TYPE_MATERIAL, _('Material')),
        (ITEM_TYPE_EQUIPMENT, _('Equipment')),
        (ITEM_TYPE_LUMP_SUM, _('Lump Sum')),
        (ITEM_TYPE_OTHER, _('Other')),
    ]
    ITEM_TYPE_VALID_CHOICES = {i[0] for i in ITEM_TYPE_CHOICES}

    ITEM_ROLE_EXPENSE = 'expense'
    ITEM_ROLE_INVENTORY = 'inventory'
    ITEM_ROLE_SERVICE = 'service'
    ITEM_ROLE_PRODUCT = 'product'
    ITEM_ROLE_CHOICES = [
        ('expense', _('Expense')),
        ('inventory', _('Inventory')),
        ('service', _('Service')),
        ('product', _('Product')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=100, verbose_name=_('Item Name'))

    item_id = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Internal ID'))
    item_number = models.CharField(max_length=30, editable=False, verbose_name=_('Item Number'))
    item_role = models.CharField(max_length=10, choices=ITEM_ROLE_CHOICES, null=True, blank=True)
    item_type = models.CharField(max_length=1, choices=ITEM_TYPE_CHOICES, null=True, blank=True)

    uom = models.ForeignKey('django_ledger.UnitOfMeasureModel',
                            verbose_name=_('Unit of Measure'),
                            on_delete=models.RESTRICT)

    sku = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('SKU Code'))
    upc = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('UPC Code'))

    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    default_amount = models.DecimalField(max_digits=20,
                                         decimal_places=2,
                                         default=0,
                                         verbose_name=_('Default monetary value per unit of measure'),
                                         validators=[MinValueValidator(0)])

    for_inventory = models.BooleanField(verbose_name=_('Is an item for inventory'),
                                        help_text=_('It is an item you require for your inventory.'))

    is_product_or_service = models.BooleanField(verbose_name=_('Is a product or service.'),
                                                help_text=_(
                                                    'Is a product or service you sell or provide to customers.'
                                                ))

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
                                       default=dict,
                                       verbose_name=_('Item Additional Info'))

    # todo: rename to entity_model...
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('Item Entity'))

    objects = ItemModelManager.from_queryset(queryset_class=ItemModelQuerySet)()

    class Meta:
        abstract = True
        unique_together = [
            ('entity', 'item_number')
        ]
        indexes = [
            models.Index(fields=['item_number']),
            models.Index(fields=['item_type']),
            models.Index(fields=['item_role']),
            models.Index(fields=['upc']),
            models.Index(fields=['sku']),
            models.Index(fields=['for_inventory']),
            models.Index(fields=['is_product_or_service']),
            models.Index(fields=['is_active'])
        ]

    def __str__(self):
        if self.is_expense():
            return f'Expense: {self.name} | {self.get_item_type_display()}'
        elif self.is_inventory():
            return f'Inventory: {self.name} | {self.get_item_type_display()}'
        elif self.is_service():
            return f'Service: {self.name} | {self.get_item_type_display()}'
        elif self.is_product():
            return f'Product: {self.name}'
        return f'Item Model: {self.name} - {self.sku} | {self.get_item_type_display()}'

    def is_expense(self):
        if self.item_role:
            return self.item_role == self.ITEM_ROLE_EXPENSE
        if all([
            not self.is_product_or_service,
            not self.for_inventory
        ]):
            self.item_role = self.ITEM_ROLE_EXPENSE
            return True
        return False

    def is_inventory(self):
        if self.item_role:
            return self.item_role == self.ITEM_ROLE_INVENTORY

        if all([
            not self.is_product_or_service,
            self.for_inventory,
        ]):
            self.item_role = self.ITEM_ROLE_INVENTORY
            return True
        return False

    def is_product(self):
        if self.item_role:
            return self.item_role == self.ITEM_ROLE_PRODUCT

        if all([
            self.is_product_or_service,
            self.for_inventory,
            not self.is_labor()
        ]):
            self.item_role = self.ITEM_ROLE_PRODUCT
            return True
        return False

    def is_service(self):
        if self.item_role:
            return self.item_role == self.ITEM_ROLE_SERVICE
        if all([
            self.is_product_or_service,
            not self.for_inventory,
            self.is_labor()
        ]):
            self.item_role = self.ITEM_ROLE_SERVICE
            return True
        return False

    def product_or_service_display(self):
        if self.is_product():
            return 'product'
        elif self.is_service():
            return 'service'

    def is_labor(self):
        return self.item_type == self.ITEM_TYPE_LABOR

    def is_material(self):
        return self.item_type == self.ITEM_TYPE_MATERIAL

    def is_equipment(self):
        return self.item_type == self.ITEM_TYPE_EQUIPMENT

    def is_lump_sum(self):
        return self.item_type == self.ITEM_TYPE_LUMP_SUM

    def is_other(self):
        return self.item_type == self.ITEM_TYPE_OTHER

    def get_average_cost(self) -> Decimal:
        if self.inventory_received:
            try:
                return self.inventory_received_value / self.inventory_received
            except ZeroDivisionError:
                pass
        return Decimal('0.00')

    def get_item_number_prefix(self):
        if self.is_expense():
            return DJANGO_LEDGER_EXPENSE_NUMBER_PREFIX
        elif self.is_inventory():
            return DJANGO_LEDGER_INVENTORY_NUMBER_PREFIX
        elif self.is_product() or self.is_service():
            return DJANGO_LEDGER_PRODUCT_NUMBER_PREFIX
        raise ItemModelValidationError('Cannot determine Item Number prefix for ItemModel. '
                                       f'For Inventory: {self.for_inventory}, '
                                       f'IsProductOrService: {self.is_product_or_service}, '
                                       f'Type: {self.item_type} '
                                       f'IsLabor: {self.is_labor()} ')

    def can_generate_item_number(self) -> bool:
        return all([
            self.entity_id,
            not self.item_number
        ])

    def _get_next_state_model(self, raise_exception: bool = True):
        EntityStateModel = lazy_loader.get_entity_state_model()

        try:
            LOOKUP = {
                'entity_model_id__exact': self.entity_id,
                'key__exact': EntityStateModel.KEY_ITEM
            }

            state_model_qs = EntityStateModel.objects.filter(**LOOKUP).select_for_update()
            state_model = state_model_qs.get()
            state_model.sequence = F('sequence') + 1
            state_model.save()
            state_model.refresh_from_db()

            return state_model
        except ObjectDoesNotExist:

            LOOKUP = {
                'entity_model_id': self.entity_id,
                'entity_unit_id': None,
                'fiscal_year': None,
                'key': EntityStateModel.KEY_ITEM,
                'sequence': 1
            }
            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model
        except IntegrityError as e:
            if raise_exception:
                raise e

    def generate_item_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next Vendor Number available.
        @param commit: Commit transaction into VendorModel.
        @return: A String, representing the current InvoiceModel instance Document Number.
        """
        if self.can_generate_item_number():
            with transaction.atomic(durable=True):

                state_model = None
                while not state_model:
                    state_model = self._get_next_state_model(raise_exception=False)

            seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
            self.item_number = f'{self.get_item_number_prefix()}-{seq}'

            if commit:
                self.save(update_fields=['item_number'])

        return self.item_number

    def save(self, **kwargs):
        if self.can_generate_item_number():
            self.generate_item_number(commit=False)
        super(ItemModelAbstract, self).save(**kwargs)

    def clean(self):

        if self.can_generate_item_number():
            self.generate_item_number(commit=False)

        if self.is_expense():
            if not self.expense_account_id:
                raise ItemModelValidationError(_('Items must have an associated expense accounts.'))
            if not self.item_type:
                raise ItemModelValidationError(_('Expenses must have a type.'))
            self.inventory_account = None
            self.earnings_account = None
            self.cogs_account = None
            self.for_inventory = False
            self.is_product_or_service = False

        elif self.is_product():
            if not all([
                self.inventory_account_id,
                self.cogs_account_id,
                self.earnings_account_id
            ]):
                raise ItemModelValidationError(_('Products must have Inventory, COGS & Earnings accounts.'))
            if self.is_labor():
                raise ItemModelValidationError(_(f'Product must not be labor...'))
            self.expense_account = None
            self.for_inventory = True
            self.is_product_or_service = True

        elif self.is_service():
            if not all([
                self.cogs_account_id,
                self.earnings_account_id
            ]):
                raise ItemModelValidationError(_('Services must have COGS & Earnings accounts.'))
            self.inventory_account = None
            self.expense_account = None
            self.for_inventory = False
            self.is_product_or_service = True
            self.item_type = self.ITEM_TYPE_LABOR

        elif self.is_inventory():
            if not all([
                self.inventory_account_id,
            ]):
                raise ItemModelValidationError(_('Items for inventory must have Inventory & COGS accounts.'))
            if not self.item_type:
                raise ItemModelValidationError(_('Inventory items must have a type.'))
            self.expense_account = None
            self.earnings_account = None
            self.for_inventory = True
            self.is_product_or_service = False


# ITEM TRANSACTION MODELS...

class ItemTransactionModelValidationError(ValidationError):
    pass


class ItemTransactionModelQuerySet(QuerySet):
    """
    QuerySet class for handling ItemTransactionModel-specific database queries.

    This class extends Django's QuerySet to provide additional methods
    to filter and retrieve specific subsets of ItemTransactionModel entries
    based on various criteria such as user permissions, transaction status,
    or custom aggregate calculations.
    """

    def for_user(self, user_model) -> 'ItemTransactionModelQuerySet':
        """
        Filters the queryset based on the provided user model.

        This method restricts the queryset to items associated with the specified
        user. If the user is a superuser, all items in the queryset are returned.
        Otherwise, only items managed or administered by the user are included.

        Parameters
        ----------
        user_model : UserModel
            The user model instance used to filter the queryset.

        Returns
        -------
        ItemTransactionModelQuerySet
            The filtered queryset containing items accessible by the given user.
        """
        if user_model.is_superuser:
            return self
        return self.filter(
            Q(item_model__entity__admin=user_model) |
            Q(item_model__entity__managers__in=[user_model])
        )

    def is_received(self) -> 'ItemTransactionModelQuerySet':
        """
        Filters the queryset to include only items with the status 'received'.

        Returns
        -------
        ItemTransactionModelQuerySet
            A queryset containing only the items with the status 'received'.
        """
        return self.filter(po_item_status=ItemTransactionModel.STATUS_RECEIVED)

    def in_transit(self) -> 'ItemTransactionModelQuerySet':
        """
        Filters and retrieves items in the "in transit" status.

        Returns
        -------
        ItemTransactionModelQuerySet
            A queryset containing items whose status is "in transit".
        """
        return self.filter(po_item_status=ItemTransactionModel.STATUS_IN_TRANSIT)

    def is_ordered(self) -> 'ItemTransactionModelQuerySet':
        """
        Filters the queryset to include only items with the status "ORDERED".

        Returns
        -------
        ItemTransactionModelQuerySet
            A filtered queryset containing items with the status "ORDERED".
        """
        return self.filter(po_item_status=ItemTransactionModel.STATUS_ORDERED)

    def is_orphan(self) -> 'ItemTransactionModelQuerySet':
        """
        Filters the query set for items that are considered "orphan", meaning
        they are not linked to any bill, purchase order, or cost estimate models.

        Returns
        -------
        ItemTransactionModelQuerySet
            A filtered query set containing only the orphan items.
        """
        return self.filter(
            Q(bill_model_id__isnull=True) &
            Q(po_model_id__isnull=True) &
            Q(ce_model_id__isnull=True)
        )

    def get_estimate_aggregate(self) -> Dict[str, int]:
        """
        Calculate aggregated estimates for cost, revenue, and total items.

        This method computes the sum of `ce_cost_estimate` and `ce_revenue_estimate`
        for all elements in the iterable, as well as the total number of items.

        Returns
        -------
        Dict[str, int]
            A dictionary containing the following keys:
                - 'ce_cost_estimate__sum': The total sum of all `ce_cost_estimate` values.
                - 'ce_revenue_estimate__sum': The total sum of all `ce_revenue_estimate` values.
                - 'total_items': The total count of items in the iterable.
        """
        return {
            'ce_cost_estimate__sum': sum(i.ce_cost_estimate for i in self),
            'ce_revenue_estimate__sum': sum(i.ce_revenue_estimate for i in self),
            'total_items': len(self)
        }


class ItemTransactionModelManager(Manager):

    def get_queryset(self) -> ItemTransactionModelQuerySet:
        """
        Provides a custom queryset for the related ItemTransactionModel.

        This method ensures that the queryset returned is an instance of the custom
        ItemTransactionModelQuerySet configured for operations on the specific model.

        Returns
        -------
        ItemTransactionModelQuerySet
            An instance of ItemTransactionModelQuerySet customized for the model.
        """
        return ItemTransactionModelQuerySet(self.model, using=self._db)

    @deprecated_entity_slug_behavior
    def for_entity(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs) -> ItemTransactionModelQuerySet:
        """
        A method to filter the queryset for a specified entity. The filtering can be performed
        using an entity model, a slug string, or a UUID. Older deprecated parameters can still
        be utilized if certain conditions are met. This method applies the necessary filters
        to the queryset based on the entity information provided.

        Parameters
        ----------
        entity_model : EntityModel | str | UUID, optional
            The entity for which the queryset is being filtered. It can be an instance of
            EntityModel, a string representing the entity slug, or a UUID corresponding to
            the entity's identifier.
        **kwargs :
            Arbitrary keyword arguments. A specific argument, `user_model`, is deprecated
            and will trigger a warning if used.

        Returns
        -------
        ItemTransactionModelQuerySet
            The queryset filtered for the specified entity.

        Raises
        ------
        ItemTransactionModelValidationError
            Raised when `entity_model` is not an instance of EntityModel, a string, or a UUID.

        Warnings
        --------
        DeprecationWarning
            Issued if `user_model` parameter is passed via kwargs. Users are encouraged to update
            their implementation to utilize `for_user(user_model).for_entity(entity_model)`
            to avoid this warning.

        Notes
        -----
        - Deprecation behavior of certain parameters depends on the `DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR` flag.
        - If `entity_model` is None, the method raises an error as entity identification is required.
        """
        EntityModel = lazy_loader.get_entity_model()

        qs = self.get_queryset()
        if 'user_model' in kwargs:
            warnings.warn(
                'user_model parameter is deprecated and will be removed in a future release. '
                'Use for_user(user_model).for_entity(entity_model) instead to keep current behavior.',
                DeprecationWarning,
                stacklevel=2
            )
            if DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR:
                qs = qs.for_user(kwargs['user_model'])

        if isinstance(entity_model, EntityModel):
            qs = qs.filter(item_model__entity=entity_model)
        elif isinstance(entity_model, str):
            qs = qs.filter(item_model__entity__slug__exact=entity_model)
        elif isinstance(entity_model, UUID):
            qs = qs.filter(item_model__entity_id=entity_model)
        else:
            raise ItemTransactionModelValidationError(
                message='Must pass EntityModel, slug or UUID'
            )
        return qs

    @deprecated_entity_slug_behavior
    def for_bill(self, bill_pk: UUID, entity_model: 'EntityModel | str | UUID' = None, **kwargs, ):
        """
        This function provides filters for fetching data related to a specific bill, based on a given
        bill primary key, along with optional parameters for an associated entity model.

        Parameters
        ----------
        bill_pk : UUID
            The primary key of the bill to filter.
        entity_model : EntityModel | str | UUID.
            Represents the associated entity model, which could be provided as an instance,
            identifier, or string.
        **kwargs : dict
            Additional filtering or query parameters.

        Returns
        -------
        QuerySet
            A filtered queryset containing data relevant to the specified bill and optional entity
            constraints.

        Deprecated
        ----------
        This function is deprecated in favor of using entity behavior. Please refer to the
        documentation for updated usage guidelines.
        """
        qs = self.for_entity(entity_model=entity_model, **kwargs)
        return qs.filter(bill_model_id__exact=bill_pk)

    @deprecated_entity_slug_behavior
    def for_invoice(self, invoice_pk: UUID, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        """
        Marks the behavior as deprecated when filtering queries for a specific invoice.

        This method provides functionality to filter a queryset based on a specified
        invoice primary key and an entity model. It is marked as deprecated in favor
        of other entity behavior methods.

        Parameters
        ----------
        invoice_pk : UUID
            The primary key of the invoice to filter the queryset by.
        entity_model : EntityModel | str | UUID
            The entity to filter the queryset for. This can be an instance of
            EntityModel, a UUID, or a string representation of the entity.
        **kwargs : dict
            Additional filtering parameters to apply to the queryset.

        Returns
        -------
        QuerySet
            A filtered queryset containing objects associated with the specified invoice.

        Raises
        ------
        Any exceptions raised during the call to `for_entity` or filtering process.

        Notes
        -----
        The method is slated for deprecation and should be replaced with preferred
        methods for filtering querysets by entity behavior in the future.
        """
        qs = self.for_entity(entity_model=entity_model, **kwargs)
        return qs.filter(invoice_model_id__exact=invoice_pk)

    @deprecated_entity_slug_behavior
    def for_po(self, po_pk: UUID, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        """
        Filters and retrieves entity records associated with a specific purchase order (PO) and entity model.

        This method applies additional filtering to an existing queryset by matching the given PO primary
        key (UUID) with records tied to the corresponding PO model. It leverages an extended filter for
        entity behavior but is marked deprecated in favor of using alternative entity filtering methods.

        Parameters
        ----------
        po_pk : UUID
            The primary key identifier for the purchase order.
        entity_model : EntityModel or str or UUID
            The model representing the associated entity. If not provided, an alternate behavior based on
            `kwargs` or contextual settings will apply.
        **kwargs : dict, optional
            Additional keyword arguments provided for extended filtering.

        Returns
        -------
        QuerySet
            A filtered queryset containing records that match the specified PO `po_pk` and entity model
            criteria.

        Raises
        ------
        None explicitly documented; refer to underlying methods (`for_entity`) for any potential errors.

        Warnings
        --------
        This method is deprecated and may be removed in future versions. Use alternative entity filtering
        methods where applicable.
        """
        qs = self.for_entity(entity_model=entity_model, **kwargs)
        return qs.filter(po_model__uuid__exact=po_pk)

    @deprecated_entity_slug_behavior
    def for_estimate(self, cj_pk: UUID, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        """
        Marks the method as deprecated for estimating behavior in relation to an entity.

        This method is intended to filter a queryset based on a specific entity and a unique
        identifier (`cj_pk`). It's discouraged to use this method in new implementations as
        it has been marked deprecated.

        Parameters
        ----------
        cj_pk : UUID
            The unique identifier for the entity model to filter on.
        entity_model : EntityModel | str | UUID
            The entity model, which may be provided either as an `EntityModel` instance,
            a string representing its identifier, or a `UUID`. Defaults to `None`.
        **kwargs : dict
            Additional keyword arguments to pass to the entity filtering mechanism.

        Returns
        -------
        QuerySet
            The filtered queryset based on the provided `cj_pk` and the optional
            `entity_model`.

        Raises
        ------
        TypeError
            If the input parameters are invalid or incompatible with the filtering process.
        """
        qs = self.for_entity(entity_model=entity_model, **kwargs)
        return qs.filter(ce_model_id__exact=cj_pk)

    @deprecated_entity_slug_behavior
    def for_contract(self, ce_pk: UUID, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        """
        Provides a method to filter querysets based on the contract entity model to which they are associated.

        Methods
        -------
        for_contract(ce_pk: UUID, entity_model: 'EntityModel | str | UUID' = None, **kwargs)
            Filters a queryset to include records associated with a specific contract entity
            model by its primary key and optionally narrows it down further using an entity model
            and additional query parameters.

        Parameters
        ----------
        ce_pk : UUID
            The unique identifier (primary key) of the contract entity model to filter by.
        entity_model : 'EntityModel | str | UUID'
            An optional entity model object, string representation, or primary key to use
            for filtering the queryset.
        **kwargs : dict
            Additional keyword arguments that can be passed to further refine the filtered queryset.

        Returns
        -------
        qs : QuerySet
            A filtered queryset containing records associated with the specified contract entity
            model and additional filter conditions.

        Raises
        ------
        Exception
            Any exception raised while applying additional filters to the queryset or querying
            against the database.

        Deprecated
        ----------
        This function is deprecated for entity behavior.
        """
        qs = self.for_entity(entity_model=entity_model, **kwargs)
        return qs.filter(
            Q(ce_model_id__exact=ce_pk) |
            Q(po_model__ce_model_id__exact=ce_pk) |
            Q(bill_model__ce_model_id__exact=ce_pk) |
            Q(invoice_model__ce_model_id__exact=ce_pk)
        )

    # INVENTORY METHODS....
    @deprecated_entity_slug_behavior
    def for_entity_inventory(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        EntityModel = lazy_loader.get_entity_model()

        qs = self.for_entity(entity_model=entity_model, **kwargs)
        if isinstance(entity_model, EntityModel):
            qs = qs.filter(item_model__entity=entity_model)
        elif isinstance(entity_model, str):
            qs = qs.filter(item_model__entity__slug__exact=entity_model)
        elif isinstance(entity_model, UUID):
            qs = qs.filter(item_model__entity_id=entity_model)
        return qs

    @deprecated_entity_slug_behavior
    def inventory_count(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        PurchaseOrderModel = lazy_loader.get_purchase_order_model()
        qs = self.for_entity_inventory(entity_model=entity_model, **kwargs)
        qs = qs.filter(
            Q(item_model__for_inventory=True) &
            (
                # received inventory...
                    (
                            Q(bill_model__isnull=False) &
                            Q(po_model__po_status=PurchaseOrderModel.PO_STATUS_APPROVED) &
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

    @deprecated_entity_slug_behavior
    def inventory_pipeline(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        qs = self.for_entity_inventory(entity_model=entity_model, **kwargs)
        return qs.filter(
            Q(item_model__for_inventory=True) &
            Q(bill_model__isnull=False) &
            Q(po_item_status__in=[
                ItemTransactionModel.STATUS_ORDERED,
                ItemTransactionModel.STATUS_IN_TRANSIT,
                ItemTransactionModel.STATUS_RECEIVED,
            ])
        )

    @deprecated_entity_slug_behavior
    def inventory_pipeline_aggregate(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        qs = self.inventory_pipeline(entity_model=entity_model, **kwargs)
        return qs.values(
            'item_model__name',
            'item_model__uom__name',
            'po_item_status').annotate(
            total_quantity=Sum('quantity'),
            total_value=Sum('total_amount')
        )

    @deprecated_entity_slug_behavior
    def inventory_pipeline_ordered(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        qs = self.inventory_pipeline(entity_model=entity_model)
        return qs.filter(po_item_status=ItemTransactionModel.STATUS_ORDERED)

    @deprecated_entity_slug_behavior
    def inventory_pipeline_in_transit(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        qs = self.inventory_pipeline(entity_model=entity_model)
        return qs.filter(po_item_status=ItemTransactionModel.STATUS_IN_TRANSIT)

    @deprecated_entity_slug_behavior
    def inventory_pipeline_received(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        qs = self.inventory_pipeline(entity_model=entity_model)
        return qs.filter(po_item_status=ItemTransactionModel.STATUS_RECEIVED)

    @deprecated_entity_slug_behavior
    def inventory_invoiced(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs):
        qs = self.for_entity_inventory(entity_model=entity_model, **kwargs)
        return qs.filter(
            Q(item_model__for_inventory=True) &
            Q(invoice_model__isnull=False)
        )


class ItemTransactionModelAbstract(CreateUpdateMixIn):
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
    objects = ItemTransactionModelManager.from_queryset(queryset_class=ItemTransactionModelQuerySet)()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['bill_model', 'item_model']),
            models.Index(fields=['invoice_model', 'item_model']),
            models.Index(fields=['po_model', 'item_model']),
            models.Index(fields=['ce_model', 'item_model']),
            models.Index(fields=['po_item_status'])
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

    def is_received(self) -> bool:
        """
        Determines if the ItemModel instance is received.
        ItemModel status is only relevant for ItemModels associated with PurchaseOrderModels.

        Returns
        -------
        bool
            True if received, else False.
        """
        return self.po_item_status == self.STATUS_RECEIVED

    def is_ordered(self) -> bool:
        """
        Determines if the ItemModel instance is ordered.
        ItemModel status is only relevant for ItemModels associated with PurchaseOrderModels.

        Returns
        -------
        bool
            True if received, else False.
        """
        return self.po_item_status == self.STATUS_RECEIVED

    def is_canceled(self):
        """
        Determines if the ItemModel instance is canceled.
        ItemModel status is only relevant for ItemModels associated with PurchaseOrderModels.

        Returns
        -------
        bool
            True if canceled, else False.
        """
        return self.po_item_status == self.STATUS_CANCELED

    # ItemTransactionModel Associations...
    def has_estimate(self) -> bool:
        """
        Determines if the ItemModel instance is associated with an EstimateModel.

        Returns
        -------
        bool
            True if associated with an EstimateModel, else False.
        """
        return self.ce_model_id is not None

    def has_po(self) -> bool:
        """
        Determines if the ItemModel instance is associated with a PurchaseOrderModel.

        Returns
        -------
        bool
            True if associated with an PurchaseOrderModel, else False.
        """
        return self.po_model_id is not None

    def has_invoice(self):
        """
        Determines if the ItemModel instance is associated with a InvoiceModel.

        Returns
        -------
        bool
            True if associated with an InvoiceModel, else False.
        """
        return self.invoice_model_id is not None

    def has_bill(self):
        """
        Determines if the ItemModel instance is associated with a BillModel.

        Returns
        -------
        bool
            True if associated with an BillModel, else False.
        """
        return self.bill_model_id is not None

    # TRANSACTIONS...
    def update_total_amount(self):
        """
        Hook that updates and checks the ItemModel instance fields according to its associations.
        Calculates and updates total_amount accordingly. Called on every clean() call.
        """
        if any([
            self.has_bill(),
            self.has_invoice(),
            self.has_po()
        ]):
            if self.quantity is None:
                self.quantity = 0.0

            if self.unit_cost is None:
                self.unit_cost = 0.0

            self.total_amount = round(Decimal.from_float(self.quantity * self.unit_cost), self.DECIMAL_PLACES)

            if self.has_po():

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
        """
        Hook that updates and checks the ItemModel instance purchase order fields according to its associations.
        Calculates and updates po_total_amount accordingly. Called on every clean() call.
        """
        if self.has_po():
            if self.po_quantity is None:
                self.po_quantity = 0.0
            if self.po_unit_cost is None:
                self.po_unit_cost = 0.0

            self.po_total_amount = round(Decimal.from_float(self.po_quantity * self.po_unit_cost), self.DECIMAL_PLACES)

    # ESTIMATE/CONTRACTS...
    def update_cost_estimate(self):
        """
        Hook that updates and checks the ItemModel instance cost estimate fields according to its associations.
        Calculates and updates ce_cost_estimate accordingly. Called on every clean() call.
        """
        if self.has_estimate():
            if self.ce_quantity is None:
                self.ce_quantity = 0.00
            if self.ce_unit_cost_estimate is None:
                self.ce_unit_cost_estimate = 0.00
            self.ce_cost_estimate = round(Decimal.from_float(self.ce_quantity * self.ce_unit_cost_estimate),
                                          self.DECIMAL_PLACES)

    def update_revenue_estimate(self):
        """
        Hook that updates and checks the ItemModel instance revenue estimate fields according to its associations.
        Calculates and updates ce_revenue_estimate accordingly. Called on every clean() call.
        """
        if self.has_estimate():
            if self.ce_quantity is None:
                self.ce_quantity = 0.00
            if self.ce_unit_revenue_estimate is None:
                self.ce_unit_revenue_estimate = 0.00
            self.ce_revenue_estimate = Decimal.from_float(self.ce_quantity * self.ce_unit_revenue_estimate)

    # HTML TAGS...
    def html_id(self) -> str:
        """
        Unique ItemModel instance HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-item-{self.uuid}'

    def html_id_unit_cost(self) -> str:
        """
        Unique ItemModel instance unit cost field HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-item-unit-cost-id-{self.uuid}'

    def html_id_quantity(self) -> str:
        """
        Unique ItemModel instance quantity field HTML ID.

        Returns
        _______
        str
            HTML ID as a String.
        """
        return f'djl-item-quantity-id-{self.uuid}'

    def can_create_bill(self) -> bool:
        """
        Determines if the ItemModel instance can be associated with a BillModel.
        Returns
        -------
        bool
            True, if instance can be associated with a BillModel, else False.
        """
        return self.bill_model_id is None and self.po_item_status in [
            self.STATUS_ORDERED,
            self.STATUS_IN_TRANSIT,
            self.STATUS_RECEIVED
        ]

    def get_status_css_class(self) -> str:
        """
        Determines the CSS Class used to represent the ItemModel instance in the UI based on its status.

        Returns
        -------
        str
            The CSS class as a String.
        """
        if self.is_received():
            return ' is-success'
        elif self.is_canceled():
            return ' is-danger'
        elif self.is_ordered():
            return ' is-info'
        return ' is-warning'

    def clean(self):
        if self.has_po() and not self.po_item_status:
            self.po_item_status = self.STATUS_NOT_ORDERED

        self.update_po_total_amount()
        self.update_cost_estimate()
        self.update_revenue_estimate()
        self.update_total_amount()


# FINAL MODEL CLASSES....
class UnitOfMeasureModel(UnitOfMeasureModelAbstract):
    """
    Base UnitOfMeasureModel from Abstract.
    """

    class Meta(UnitOfMeasureModelAbstract.Meta):
        abstract = False


class ItemTransactionModel(ItemTransactionModelAbstract):
    """
    Base ItemTransactionModel from Abstract.
    """

    class Meta(ItemTransactionModelAbstract.Meta):
        abstract = False


class ItemModel(ItemModelAbstract):
    """
    Base ItemModel from Abstract.
    """

    class Meta(ItemModelAbstract.Meta):
        abstract = False
