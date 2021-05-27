"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from random import choices
from string import ascii_uppercase, digits
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, Count
from django.utils.translation import gettext_lazy as _

from django_ledger.models import EntityModel
from django_ledger.models.mixins import CreateUpdateMixIn, ItemTotalCostMixIn

PO_NUMBER_CHARS = ascii_uppercase + digits


def generate_po_number(length: int = 10, prefix: bool = True) -> str:
    """
    A function that generates a random PO identifier for new PO models.
    :param prefix:
    :param length: The length of the bill number.
    :return: A string representing a random bill identifier.
    """
    po_number = ''.join(choices(PO_NUMBER_CHARS, k=length))
    if prefix:
        po_number = 'PO-' + po_number
    return po_number


class PurchaseOrderModelManager(models.Manager):

    def for_entity(self, entity_slug, user_model):
        qs = self.get_queryset()
        if isinstance(entity_slug, EntityModel):
            return qs.filter(
                Q(ledger__entity=entity_slug) & (
                        Q(ledger__entity__admin=user_model) |
                        Q(ledger__entity__managers__in=[user_model])
                )
            )
        elif isinstance(entity_slug, str):
            return qs.filter(
                Q(ledger__entity__slug__exact=entity_slug) & (
                        Q(ledger__entity__admin=user_model) |
                        Q(ledger__entity__managers__in=[user_model])
                )
            )


class PurchaseOrderModelAbstract(CreateUpdateMixIn):
    PO_STATUS = [
        ('draft', _('Draft')),
        ('in_review', _('In Review')),
        ('approved', _('Approved'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    po_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Purchase Order Number'))
    po_date = models.DateField(verbose_name=_('Purchase Order Date'))
    po_title = models.CharField(max_length=250, verbose_name=_('Purchase Order Title'))
    po_notes = models.TextField(blank=True, null=True, verbose_name=_('Notes'))
    po_status = models.CharField(max_length=10, choices=PO_STATUS, default=PO_STATUS[0][0])
    po_amount = models.DecimalField(default=0, decimal_places=2, max_digits=20, verbose_name=_('Purchase Order Amount'))
    vendor = models.ForeignKey('django_ledger.VendorModel', blank=True, null=True, on_delete=models.PROTECT)
    ledger = models.OneToOneField('django_ledger.LedgerModel',
                                  verbose_name=_('Ledger'),
                                  on_delete=models.CASCADE)
    for_inventory = models.BooleanField(verbose_name=_('Inventory Purchase?'))
    fulfillment_date = models.DateField(blank=True, null=True, verbose_name=_('Fulfillment Date'))

    po_items = models.ManyToManyField('django_ledger.ItemModel',
                                      through='django_ledger.PurchaseOrderItemThroughModel',
                                      verbose_name=_('Purchase Order Items'))

    objects = PurchaseOrderModelManager()

    class Meta:
        abstract = True

    def __str__(self):
        return f'PO Model: {self.po_number} | {self.get_po_status_display()}'

    def clean(self):
        if not self.po_number:
            self.po_number = generate_po_number()
        if any([
            self.po_status == self.PO_STATUS[1][0],
            self.po_status == self.PO_STATUS[2][0],
        ]):
            if not self.vendor:
                raise ValidationError(message=f'Must provide a Vendor for this PO')

    def get_po_item_data(self, queryset=None) -> tuple:
        if not queryset:
            queryset = self.pomodelitemsthroughmodel_set.all()
        return queryset, queryset.aggregate(
            amount_due=Sum('total_amount'),
            total_items=Count('uuid')
        )


class PurchaseOrderItemThroughModelManager(models.Manager):

    def for_entity(self, entity_slug, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(po_model__ledger__entity_model__slug__exact=entity_slug) &
            (
                    Q(po_model__ledger__entity_model__managers__in=[user_model]) |
                    Q(po_model__ledger__entity_model__admin=user_model)

            )
        )

    def for_po(self, entity_slug, user_model, po_pk):
        qs = self.for_entity(entity_slug, user_model)
        return qs.filter(po_model__uuid__exact=po_pk)


class PurchaseOrderItemThroughModelAbstract(ItemTotalCostMixIn, CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    po_model = models.ForeignKey('django_ledger.PurchaseOrderModel',
                                 on_delete=models.CASCADE,
                                 verbose_name=_('PO Item'))

    objects = PurchaseOrderItemThroughModelManager()

    class Meta:
        abstract = True


class PurchaseOrderModel(PurchaseOrderModelAbstract):
    """
    Purchase Order Base Model
    """


class PurchaseOrderItemThroughModel(PurchaseOrderItemThroughModelAbstract):
    """
    Purchase Order Item Base Model
    """
