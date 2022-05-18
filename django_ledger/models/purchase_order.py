"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
import datetime
from decimal import Decimal
from random import choices
from string import ascii_uppercase, digits
from typing import Tuple, List, Union
from uuid import uuid4

from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, Count, QuerySet
from django.shortcuts import get_object_or_404
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


class PurchaseOrderModelAbstract(CreateUpdateMixIn, MarkdownNotesMixIn):
    # todo: having a fulfilled field is not necessary if PO can have a PO_STATUS_FULFILLED.

    PO_STATUS_DRAFT = 'draft'
    PO_STATUS_REVIEW = 'in_review'
    PO_STATUS_APPROVED = 'approved'
    PO_STATUS_CANCELED = 'canceled'
    PO_STATUS_FULFILLED = 'fulfilled'

    PO_STATUS = [
        (PO_STATUS_DRAFT, _('Draft')),
        (PO_STATUS_REVIEW, _('In Review')),
        (PO_STATUS_APPROVED, _('Approved')),
        (PO_STATUS_CANCELED, _('Canceled')),
        (PO_STATUS_FULFILLED, _('Fulfilled')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    po_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Purchase Order Number'))
    po_date = models.DateField(verbose_name=_('Purchase Order Date'), null=True, blank=True)
    po_title = models.CharField(max_length=250,
                                verbose_name=_('Purchase Order Title'),
                                validators=[
                                    MinLengthValidator(limit_value=5,
                                                       message=_(
                                                           f'PO Title must be greater than 5'))
                                ])
    po_status = models.CharField(max_length=10, choices=PO_STATUS, default=PO_STATUS[0][0])
    po_amount = models.DecimalField(default=0, decimal_places=2, max_digits=20, verbose_name=_('Purchase Order Amount'))
    po_amount_received = models.DecimalField(default=0,
                                             decimal_places=2,
                                             max_digits=20,
                                             verbose_name=_('Received Amount'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Entity'))
    # fulfilled = models.BooleanField(default=False, verbose_name=_('Is Fulfilled'))
    fulfillment_date = models.DateField(blank=True, null=True, verbose_name=_('Fulfillment Date'))

    # todo: sIs this M2M field???....
    po_items = models.ManyToManyField('django_ledger.ItemModel',
                                      through='django_ledger.ItemThroughModel',
                                      through_fields=('po_model', 'item_model'),
                                      verbose_name=_('Purchase Order Items'))

    ce_model = models.ForeignKey('django_ledger.EstimateModel',
                                 on_delete=models.RESTRICT,
                                 null=True,
                                 blank=True,
                                 verbose_name=_('Associated Customer Job/Estimate'))

    objects = PurchaseOrderModelManager()

    class Meta:
        abstract = True

    def __str__(self):
        # pylint: disable=no-member
        return f'PO Model: {self.po_number} | {self.get_po_status_display()}'

    # Configuration...
    def configure(self,
                  entity_slug: str or EntityModel,
                  user_model,
                  po_date: datetime.date = None):
        if isinstance(entity_slug, str):
            entity_qs = EntityModel.objects.for_user(
                user_model=user_model)
            entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')

        self.po_number = generate_po_number()
        if po_date:
            self.po_date = po_date
        self.entity = entity_model
        return self

    # State Update...
    def get_po_item_data(self, queryset: QuerySet = None) -> Tuple:
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemthroughmodel_set.all().select_related('bill_model')

        return queryset, queryset.aggregate(
            amount_due=Sum('po_total_amount'),
            total_paid=Sum('bill_model__amount_paid'),
            total_items=Count('uuid')
        )

    def update_po_state(self,
                        item_queryset: QuerySet = None,
                        item_list: List[ItemThroughModel] = None) -> Union[Tuple, None]:
        if item_queryset and item_list:
            raise ValidationError('Either queryset or list can be used.')

        if item_list:
            # self.po_amount = Decimal.from_float(
            #     round(sum(a.po_total_amount for a in item_list
            #               if a.po_item_status != ItemThroughModel.STATUS_CANCELED), 2))
            self.po_amount = sum(
                a.po_total_amount for a in item_list if a.po_item_status != ItemThroughModel.STATUS_CANCELED)

            # self.po_amount_received = Decimal.from_float(
            #     round(sum(a.po_total_amount for a in item_list
            #               if a.po_item_status == ItemThroughModel.STATUS_RECEIVED), 2))
            self.po_amount_received = sum(
                a.po_total_amount for a in item_list if a.po_item_status == ItemThroughModel.STATUS_RECEIVED)
        else:

            # todo: explore if queryset can be passed from PO Update View...
            item_queryset, item_data = self.get_po_item_data(queryset=item_queryset)
            qs_values = item_queryset.values(
                'po_total_amount', 'po_item_status'
            )
            total_po_amount = sum(
                i['po_total_amount'] for i in qs_values if i['po_item_status'] != ItemThroughModel.STATUS_CANCELED
            )
            total_received = sum(
                i['po_total_amount'] for i in qs_values if i['po_item_status'] == ItemThroughModel.STATUS_RECEIVED
            )
            self.po_amount = total_po_amount
            self.po_amount_received = total_received
            return item_queryset, item_data

    # State...
    def is_draft(self):
        return self.po_status == self.PO_STATUS_DRAFT

    def is_review(self):
        return self.po_status == self.PO_STATUS_REVIEW

    def is_approved(self):
        return self.po_status == self.PO_STATUS_APPROVED

    def is_canceled(self):
        return self.po_status == self.PO_STATUS_CANCELED

    def is_fulfilled(self):
        return self.po_status == self.PO_STATUS_FULFILLED

    # Permissions...
    def can_draft(self):
        return self.is_review()

    def can_review(self):
        return self.is_draft()

    def can_approve(self):
        return self.is_review() and self.po_date

    def can_cancel(self):
        return self.is_approved()

    def can_fulfill(self):
        return self.is_approved()

    def can_delete(self):
        return self.po_status in {
            self.PO_STATUS_DRAFT,
            self.PO_STATUS_REVIEW
        }

    def can_void(self):
        raise NotImplementedError()

    def can_edit_items(self):
        return self.is_draft()

    # Actions...
    def mark_as_draft(self, commit: bool = False):
        if not self.can_draft():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as draft.')
        self.po_status = self.PO_STATUS_DRAFT
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'updated'
            ])

    def mark_as_review(self, commit: bool = False):
        if not self.can_review():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as in review.')
        itemthrough_qs = self.itemthroughmodel_set.all()
        if not itemthrough_qs.count():
            raise ValidationError(message='Cannot review a PO without items...')
        if not self.po_amount:
            raise ValidationError(message='PO amount is zero.')
        self.po_status = self.PO_STATUS_REVIEW
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'updated'
            ])

    def mark_as_approved(self, commit: bool = False):
        if not self.can_approve():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as approved.')
        self.po_status = self.PO_STATUS_APPROVED
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'updated'
            ])

    def mark_as_canceled(self, commit: bool = False):
        if not self.can_cancel():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as canceled.')
        self.po_status = self.PO_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'updated'
            ])

    def mark_as_fulfilled(self,
                          fulfilled_date: datetime.date = None,
                          po_items: Union[QuerySet, List[ItemThroughModel]] = None,
                          commit=False):
        if not self.can_fulfill():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as fulfilled.')
        if not fulfilled_date:
            self.fulfillment_date = localdate()

        if not fulfilled_date and not self.po_date:
            fulfilled_date = localdate()

        elif fulfilled_date and self.po_date:
            if fulfilled_date < self.po_date:
                raise ValidationError(f'Cannot fulfill PO with date earlier than PO date {self.po_date}')

        if not po_items:
            po_items, agg = self.get_po_item_data()

        bill_models = [i.bill_model for i in po_items]

        all_items_billed = all(bill_models)
        if not all_items_billed:
            raise ValidationError('All items must be billed before PO can be fulfilled.')

        all_bills_paid = all(b.is_paid() for b in bill_models)
        if not all_bills_paid:
            raise ValidationError('All Bills must be paid before PO can be fulfilled.')

        self.fulfillment_date = fulfilled_date
        self.po_status = self.PO_STATUS_FULFILLED

        self.clean()

        if commit:
            update_fields = [
                'fulfillment_date',
                'po_status',
                'updated'
            ]
            self.save(update_fields=update_fields)

    # Validation...
    def clean(self):
        if not self.po_number:
            self.po_number = generate_po_number()
        # if self.is_fulfilled() and not self.is_approved():
        #     raise ValidationError('Can only fulfill POs that has been approved.')

        if self.is_approved() and self.po_date:
            if self.po_date > localdate():
                raise ValidationError('PO cannot have a future approval date.')
        if self.is_approved() and not self.po_date:
            self.po_date = localdate()
        # if self.fulfillment_date:
        #     self.fulfilled = True
        if self.is_fulfilled():
            self.po_amount_received = self.po_amount
        if self.is_fulfilled() and not self.fulfillment_date:
            self.fulfillment_date = localdate()


class PurchaseOrderModel(PurchaseOrderModelAbstract):
    """
    Purchase Order Base Model
    """
