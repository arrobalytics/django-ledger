"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from datetime import date
from random import choices
from string import ascii_uppercase, digits
from typing import Tuple, List, Union
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q, Sum, Count, QuerySet
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.models import EntityModel, ItemThroughModel, LazyLoader, BillModel
from django_ledger.models.mixins import CreateUpdateMixIn, MarkdownNotesMixIn

PO_NUMBER_CHARS = ascii_uppercase + digits

lazy_loader = LazyLoader()


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
    PO_STATUS_FULFILLED = 'fulfilled'
    PO_STATUS_VOID = 'void'
    PO_STATUS_CANCELED = 'canceled'

    PO_STATUS = [
        (PO_STATUS_DRAFT, _('Draft')),
        (PO_STATUS_REVIEW, _('In Review')),
        (PO_STATUS_APPROVED, _('Approved')),
        (PO_STATUS_FULFILLED, _('Fulfilled')),
        (PO_STATUS_CANCELED, _('Canceled')),
        (PO_STATUS_VOID, _('Void')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    po_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Purchase Order Number'))
    # todo: remove PO date from model in favor of state dates... (draft)...
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

    draft_date = models.DateField(null=True, blank=True, verbose_name=_('Draft Date'))
    in_review_date = models.DateField(null=True, blank=True, verbose_name=_('In Review Date'))
    approved_date = models.DateField(null=True, blank=True, verbose_name=_('Approved Date'))
    void_date = models.DateField(blank=True, null=True, verbose_name=_('Void Date'))
    fulfillment_date = models.DateField(blank=True, null=True, verbose_name=_('Fulfillment Date'))
    canceled_date = models.DateField(null=True, blank=True, verbose_name=_('Canceled Date'))

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
                  po_date: date = None):
        if isinstance(entity_slug, str):
            entity_qs = EntityModel.objects.for_user(
                user_model=user_model)
            entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')

        self.po_number = generate_po_number()
        # if po_date:
        #     self.po_date = po_date
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

    # todo: check if all update ste methods can accept a queryset only...
    def update_po_state(self,
                        item_queryset: QuerySet = None,
                        item_list: List[ItemThroughModel] = None) -> Union[Tuple, None]:
        if item_queryset and item_list:
            raise ValidationError('Either queryset or list can be used.')

        if item_list:
            self.po_amount = round(sum(
                a.po_total_amount for a in item_list if a.po_item_status != ItemThroughModel.STATUS_CANCELED), 2)
            self.po_amount_received = round(sum(
                a.po_total_amount for a in item_list if a.is_received()), 2)
        else:
            item_queryset, item_data = self.get_po_item_data(queryset=item_queryset)
            total_po_amount = round(sum(i.po_total_amount for i in item_queryset if not i.is_canceled()), 2)
            total_received = round(sum(i.po_total_amount for i in item_queryset if i.is_received()), 2)
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

    def is_fulfilled(self):
        return self.po_status == self.PO_STATUS_FULFILLED

    def is_canceled(self):
        return self.po_status == self.PO_STATUS_CANCELED

    def is_void(self):
        return self.po_status == self.PO_STATUS_VOID

    # Permissions...
    def can_draft(self):
        return self.is_review()

    def can_review(self):
        return self.is_draft()

    def can_approve(self):
        return self.is_review()

    def can_fulfill(self):
        return self.is_approved()

    def can_cancel(self):
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_void(self):
        return self.is_approved()

    def can_delete(self):
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_edit_items(self):
        return self.is_draft()

    # Actions...
    # DRAFT...
    def mark_as_draft(self, commit: bool = False, **kwargs):
        if not self.can_draft():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as draft.')
        self.po_status = self.PO_STATUS_DRAFT
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'updated'
            ])

    def get_mark_as_draft_html_id(self):
        return f'djl-{self.uuid}-po-mark-as-draft'

    def get_mark_as_draft_url(self):
        return reverse('django_ledger:po-action-mark-as-draft',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_draft_message(self):
        return _('Do you want to mark Purchase Order %s as Draft?') % self.po_number

    # REVIEW...
    def mark_as_review(self, date_review: date = None, commit: bool = False, **kwargs):
        if not self.can_review():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as in review.')
        itemthrough_qs = self.itemthroughmodel_set.all()
        if not itemthrough_qs.count():
            raise ValidationError(message='Cannot review a PO without items...')
        if not self.po_amount:
            raise ValidationError(message='PO amount is zero.')

        self.in_review_date = localdate() if not date_review else date_review
        self.po_status = self.PO_STATUS_REVIEW
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'in_review_date',
                'updated'
            ])

    def get_mark_as_review_html_id(self):
        return f'djl-{self.uuid}-po-mark-as-review'

    def get_mark_as_review_url(self):
        return reverse('django_ledger:po-action-mark-as-review',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_review_message(self):
        return _('Do you want to mark Purchase Order %s as In Review?') % self.po_number

    # APPROVED...
    def mark_as_approved(self, commit: bool = False, date_approved: date = None, **kwargs):
        if not self.can_approve():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as approved.')
        self.approved_date = localdate() if not date_approved else date_approved
        self.po_status = self.PO_STATUS_APPROVED
        self.clean()
        if commit:
            self.itemthroughmodel_set.all().update(po_item_status=ItemThroughModel.STATUS_NOT_ORDERED)
            self.save(update_fields=[
                'approved_date',
                'po_status',
                'updated'
            ])

    def get_mark_as_approved_html_id(self):
        return f'djl-{self.uuid}-po-mark-as-approved'

    def get_mark_as_approved_url(self):
        return reverse('django_ledger:po-action-mark-as-approved',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_approved_message(self):
        return _('Do you want to mark Purchase Order %s as Approved?') % self.po_number

    # CANCEL...
    def mark_as_canceled(self, commit: bool = False, date_canceled: date = None, **kwargs):
        if not self.can_cancel():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as canceled.')
        self.canceled_date = localdate() if not date_canceled else date_canceled
        self.po_status = self.PO_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'canceled_date',
                'updated'
            ])

    def get_mark_as_canceled_html_id(self):
        return f'djl-{self.uuid}-po-mark-as-canceled'

    def get_mark_as_canceled_url(self):
        return reverse('django_ledger:po-action-mark-as-canceled',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_canceled_message(self):
        return _('Do you want to mark Purchase Order %s as Canceled?') % self.po_number

    # FULFILL...
    def mark_as_fulfilled(self,
                          date_fulfilled: date = None,
                          po_items: Union[QuerySet, List[ItemThroughModel]] = None,
                          commit=False,
                          **kwargs):
        if not self.can_fulfill():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as fulfilled.')
        self.fulfillment_date = localdate() if not date_fulfilled else date_fulfilled

        if not po_items:
            po_items = self.itemthroughmodel_set.all().select_related('bill_model')

        bill_models = [i.bill_model for i in po_items]
        all_items_billed = all(bill_models)
        if not all_items_billed:
            raise ValidationError('All items must be billed before PO can be fulfilled.')

        all_bills_paid = all(b.is_paid() for b in bill_models)
        if not all_bills_paid:
            raise ValidationError('All Bills must be paid before PO can be fulfilled.')

        all_items_received = all(i.is_received() for i in po_items)
        if not all_items_received:
            raise ValidationError('All items must be received before PO is fulfilled.')

        self.fulfillment_date = date_fulfilled
        self.po_status = self.PO_STATUS_FULFILLED
        self.clean()

        if commit:
            po_items.update(po_item_status=ItemThroughModel.STATUS_RECEIVED)
            self.save(update_fields=[
                'fulfillment_date',
                'po_status',
                'updated'
            ])

    def get_mark_as_fulfilled_html_id(self):
        return f'djl-{self.uuid}-po-mark-as-fulfilled'

    def get_mark_as_fulfilled_url(self):
        return reverse('django_ledger:po-action-mark-as-fulfilled',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_fulfilled_message(self):
        return _('Do you want to mark Purchase Order %s as Fulfilled?') % self.po_number

    # VOID...
    def mark_as_void(self,
                     entity_slug: str,
                     user_model,
                     void_date: date = None,
                     commit=False,
                     **kwargs):
        if not self.can_void():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as void.')

        # all bills associated with this PO...
        bill_model_qs = self.get_po_bill_queryset(
            entity_slug=entity_slug,
            user_model=user_model
        )
        bill_model_qs = bill_model_qs.only('bill_status')

        if not all(b.is_void() for b in bill_model_qs):
            raise ValidationError('Must void all PO bills before PO can be voided.')

        self.void_date = localdate() if not void_date else void_date
        self.po_status = self.PO_STATUS_VOID
        self.clean()

        if commit:
            self.save(update_fields=[
                'void_date',
                'po_status',
                'updated'
            ])

    def get_mark_as_void_html_id(self):
        return f'djl-{self.uuid}-po-mark-as-void'

    def get_mark_as_void_url(self):
        return reverse('django_ledger:po-action-mark-as-void',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'po_pk': self.uuid
                       })

    def get_mark_as_void_message(self):
        return _('Do you want to mark Purchase Order %s as Void?') % self.po_number

    # Conevience Methods...

    def get_po_bill_queryset(self, user_model, entity_slug):
        return BillModel.objects.for_entity(
            user_model=user_model,
            entity_slug=entity_slug
        ).filter(bill_items__purchaseordermodel__uuid__exact=self.uuid)

    def clean(self):
        if not self.po_number:
            self.po_number = generate_po_number()
        # if self.is_approved() and self.po_date:
        #     if self.po_date > localdate():
        #         raise ValidationError('PO cannot have a future approval date.')
        # if self.is_approved() and not self.po_date:
        #     self.po_date = localdate()
        if self.is_fulfilled():
            self.po_amount_received = self.po_amount
        if self.is_fulfilled() and not self.fulfillment_date:
            self.fulfillment_date = localdate()


class PurchaseOrderModel(PurchaseOrderModelAbstract):
    """
    Purchase Order Base Model
    """
