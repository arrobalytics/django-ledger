"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from decimal import Decimal
from random import choices
from string import ascii_uppercase, digits
from uuid import uuid4

from django.db import models
from django.db.models import Q, Sum, Count
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.models import EntityModel, ItemThroughModel
from django_ledger.models.mixins import CreateUpdateMixIn, MarkdownNotesMixIn

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
            qs = qs.filter(entity=entity_slug)
        elif isinstance(entity_slug, str):
            qs = qs.filter(entity__slug__exact=entity_slug)
        return qs.filter(
            Q(entity__admin=user_model) |
            Q(entity__managers__in=[user_model])
        )


class PurchaseOrderModelAbstract(CreateUpdateMixIn,
                                 MarkdownNotesMixIn):
    PO_STATUS_DRAFT = 'draft'
    PO_STATUS_REVIEW = 'in_review'
    PO_STATUS_APPROVED = 'approved'

    PO_STATUS = [
        (PO_STATUS_DRAFT, _('Draft')),
        (PO_STATUS_REVIEW, _('In Review')),
        (PO_STATUS_APPROVED, _('Approved'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    po_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Purchase Order Number'))
    po_date = models.DateField(verbose_name=_('Purchase Order Date'))
    po_title = models.CharField(max_length=250, verbose_name=_('Purchase Order Title'))
    po_status = models.CharField(max_length=10, choices=PO_STATUS, default=PO_STATUS[0][0])
    po_amount = models.DecimalField(default=0, decimal_places=2, max_digits=20, verbose_name=_('Purchase Order Amount'))
    po_amount_received = models.DecimalField(default=0,
                                             decimal_places=2,
                                             max_digits=20,
                                             verbose_name=_('Received Amount'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Entity'))
    fulfilled = models.BooleanField(default=False, verbose_name=_('Is Fulfilled'))
    fulfillment_date = models.DateField(blank=True, null=True, verbose_name=_('Fulfillment Date'))

    po_items = models.ManyToManyField('django_ledger.ItemModel',
                                      through='django_ledger.ItemThroughModel',
                                      through_fields=('po_model', 'item_model'),
                                      verbose_name=_('Purchase Order Items'))

    objects = PurchaseOrderModelManager()

    class Meta:
        abstract = True

    def __str__(self):
        return f'PO Model: {self.po_number} | {self.get_po_status_display()}'

    def clean(self):
        if not self.po_number:
            self.po_number = generate_po_number()
        if self.fulfillment_date:
            self.fulfilled = True
        if self.fulfilled:
            self.po_amount_received = self.po_amount
        if self.fulfilled and not self.fulfillment_date:
            self.fulfillment_date = localdate()

    def get_po_item_data(self, queryset=None) -> tuple:
        if not queryset:
            queryset = self.itemthroughmodel_set.all()
        return queryset, queryset.aggregate(
            amount_due=Sum('total_amount'),
            total_paid=Sum('bill_model__amount_paid'),
            total_items=Count('uuid')
        )

    def update_po_state(self, queryset=None, item_list: list = None) -> None or tuple:
        if item_list:
            self.amount_due = Decimal.from_float(round(sum(a.total_amount for a in item_list), 2))
            return

        # todo: explore if queryset can be passed from PO Update View...
        queryset, item_data = self.get_po_item_data(queryset=queryset)
        qs_values = queryset.values(
            'total_amount', 'po_item_status'
        )
        total_received = sum(
            i['total_amount'] for i in qs_values if i['po_item_status'] == ItemThroughModel.STATUS_RECEIVED
        )
        total_po_amount = sum(
            i['total_amount'] for i in qs_values if i['po_item_status'] != ItemThroughModel.STATUS_CANCELED
        )
        self.po_amount = total_po_amount
        self.po_amount_received = total_received
        return queryset, item_data


class PurchaseOrderModel(PurchaseOrderModelAbstract):
    """
    Purchase Order Base Model
    """
