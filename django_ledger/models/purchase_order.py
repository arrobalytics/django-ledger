"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
Pranav P Tulshyan <Ptulshyan77@gmail.com>
"""
from datetime import date
from string import ascii_uppercase, digits
from typing import Tuple, List, Union
from uuid import uuid4

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinLengthValidator
from django.db import models, transaction
from django.db.models import Q, Sum, Count, QuerySet, Case, When, Value, ExpressionWrapper, IntegerField, F
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.models import EntityModel, ItemTransactionModel, LazyLoader, BillModel
from django_ledger.models.mixins import CreateUpdateMixIn, MarkdownNotesMixIn
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_PO_NUMBER_PREFIX

PO_NUMBER_CHARS = ascii_uppercase + digits

lazy_loader = LazyLoader()


class PurchaseOrderModelQueryset(models.QuerySet):

    def approved(self):
        return self.filter(po_status__exact=PurchaseOrderModel.PO_STATUS_APPROVED)

    def fulfilled(self):
        return self.filter(po_status__exact=PurchaseOrderModel.PO_STATUS_FULFILLED)

    def active(self):
        return self.filter(
            Q(po_status__exact=PurchaseOrderModel.PO_STATUS_APPROVED) |
            Q(po_status__exact=PurchaseOrderModel.PO_STATUS_FULFILLED)
        )


class PurchaseOrderModelManager(models.Manager):

    def get_queryset(self):
        return PurchaseOrderModelQueryset(self.model, using=self._db)

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
    po_number = models.SlugField(max_length=20, verbose_name=_('Purchase Order Number'), editable=False)
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

    date_draft = models.DateField(null=True, blank=True, verbose_name=_('Draft Date'))
    date_in_review = models.DateField(null=True, blank=True, verbose_name=_('In Review Date'))
    date_approved = models.DateField(null=True, blank=True, verbose_name=_('Approved Date'))
    date_void = models.DateField(blank=True, null=True, verbose_name=_('Void Date'))
    date_fulfilled = models.DateField(blank=True, null=True, verbose_name=_('Fulfillment Date'))
    date_canceled = models.DateField(null=True, blank=True, verbose_name=_('Canceled Date'))

    po_items = models.ManyToManyField('django_ledger.ItemModel',
                                      through='django_ledger.ItemTransactionModel',
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
        indexes = [
            models.Index(fields=['entity', 'po_number']),
            models.Index(fields=['po_status']),
            models.Index(fields=['ce_model']),

            models.Index(fields=['date_draft']),
            models.Index(fields=['date_in_review']),
            models.Index(fields=['date_approved']),
            models.Index(fields=['date_fulfilled']),
            models.Index(fields=['date_canceled']),
            models.Index(fields=['date_void']),
        ]
        unique_together = [
            ('entity', 'po_number')
        ]

    def __str__(self):
        # pylint: disable=no-member
        return f'PO Model: {self.po_number} | {self.get_po_status_display()}'

    # Configuration...
    def configure(self,
                  entity_slug: str or EntityModel,
                  user_model,
                  draft_date: date = None,
                  commit: bool = False):

        if isinstance(entity_slug, str):
            entity_qs = EntityModel.objects.for_user(
                user_model=user_model)
            entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')

        if draft_date:
            self.date_draft = draft_date
        if not self.date_draft:
            self.date_draft = localdate()
        self.entity = entity_model
        self.clean()
        if commit:
            self.save()
        return self

    # State Update...
    def get_itemtxs_data(self, queryset: QuerySet = None) -> Tuple:
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemtransactionmodel_set.all().select_related('bill_model', 'item_model')

        return queryset, queryset.aggregate(
            po_total_amount__sum=Coalesce(Sum('po_total_amount'), 0.0, output_field=models.FloatField()),
            bill_amount_paid__sum=Coalesce(Sum('bill_model__amount_paid'), 0.0, output_field=models.FloatField()),
            total_items=Count('uuid')
        )

    def update_state(self,
                     itemtxs_qs: QuerySet = None,
                     itemtxs_list: List[ItemTransactionModel] = None) -> Union[Tuple, None]:
        if itemtxs_qs and itemtxs_list:
            raise ValidationError('Either queryset or list can be used.')

        if itemtxs_list:
            self.po_amount = round(sum(a.po_total_amount for a in itemtxs_list if not a.is_canceled()), 2)
            self.po_amount_received = round(sum(a.po_total_amount for a in itemtxs_list if a.is_received()), 2)
        else:
            itemtxs_qs, itemtxs_agg = self.get_itemtxs_data(queryset=itemtxs_qs)
            total_po_amount = round(sum(i.po_total_amount for i in itemtxs_qs if not i.is_canceled()), 2)
            total_received = round(sum(i.po_total_amount for i in itemtxs_qs if i.is_received()), 2)
            self.po_amount = total_po_amount
            self.po_amount_received = total_received
            return itemtxs_qs, itemtxs_agg

    # State...
    def is_draft(self) -> bool:
        return self.po_status == self.PO_STATUS_DRAFT

    def is_review(self) -> bool:
        return self.po_status == self.PO_STATUS_REVIEW

    def is_approved(self) -> bool:
        return self.po_status == self.PO_STATUS_APPROVED

    def is_fulfilled(self) -> bool:
        return self.po_status == self.PO_STATUS_FULFILLED

    def is_canceled(self) -> bool:
        return self.po_status == self.PO_STATUS_CANCELED

    def is_void(self) -> bool:
        return self.po_status == self.PO_STATUS_VOID

    # Permissions...
    def can_draft(self) -> bool:
        return self.is_review()

    def can_review(self) -> bool:
        return self.is_draft()

    def can_approve(self) -> bool:
        return self.is_review()

    def can_fulfill(self) -> bool:
        return self.is_approved()

    def can_cancel(self) -> bool:
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_void(self) -> bool:
        return self.is_approved()

    def can_delete(self) -> bool:
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_edit_items(self) -> bool:
        return self.is_draft()

    def is_contract_bound(self):
        return self.ce_model_id is not None

    def can_bind_estimate(self, estimate_model, raise_exception: bool = False) -> bool:
        if self.is_contract_bound():
            if raise_exception:
                raise ValidationError(f'PO {self.po_number} already bound to Estimate {self.ce_model.estimate_number}')
            return False
        # check if estimate_model is passed and raise exception if needed...
        is_approved = estimate_model.is_approved()
        if not is_approved and raise_exception:
            raise ValidationError(f'Cannot bind estimate that is not approved.')
        return all([
            is_approved
        ])

    def can_generate_po_number(self):
        return all([
            self.date_draft,
            not self.po_number
        ])

    # Actions...
    def action_bind_estimate(self, estimate_model, commit: bool = False):
        try:
            self.can_bind_estimate(estimate_model, raise_exception=True)
        except ValueError as e:
            raise e
        self.ce_model = estimate_model
        self.clean()
        if commit:
            self.save(update_fields=[
                'ce_model',
                'updated'
            ])

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
        itemthrough_qs = self.itemtransactionmodel_set.all()
        if not itemthrough_qs.count():
            raise ValidationError(message='Cannot review a PO without items...')
        if not self.po_amount:
            raise ValidationError(message='PO amount is zero.')

        self.date_in_review = localdate() if not date_review else date_review
        self.po_status = self.PO_STATUS_REVIEW
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'date_in_review',
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
        self.date_approved = localdate() if not date_approved else date_approved
        self.po_status = self.PO_STATUS_APPROVED
        self.clean()
        if commit:
            self.itemtransactionmodel_set.all().update(po_item_status=ItemTransactionModel.STATUS_NOT_ORDERED)
            self.save(update_fields=[
                'date_approved',
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
        self.date_canceled = localdate() if not date_canceled else date_canceled
        self.po_status = self.PO_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'po_status',
                'date_canceled',
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
                          po_items: Union[QuerySet, List[ItemTransactionModel]] = None,
                          commit=False,
                          **kwargs):
        if not self.can_fulfill():
            raise ValidationError(message=f'Purchase Order {self.po_number} cannot be marked as fulfilled.')
        self.date_fulfilled = localdate() if not date_fulfilled else date_fulfilled
        self.po_amount_received = self.po_amount

        if not po_items:
            po_items = self.itemtransactionmodel_set.all().select_related('bill_model')

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

        self.date_fulfilled = date_fulfilled
        self.po_status = self.PO_STATUS_FULFILLED
        self.clean()

        if commit:
            po_items.update(po_item_status=ItemTransactionModel.STATUS_RECEIVED)
            self.save(update_fields=[
                'date_fulfilled',
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

        self.date_void = localdate() if not void_date else void_date
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

    def get_status_action_date(self):
        if self.is_fulfilled():
            return self.date_fulfilled
        return getattr(self, f'date_{self.po_status}')

    def generate_po_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next PurchaseOrder document number available.
        @param raise_exception: Raises a ValidationError if PO number cannot be generated.
        @param commit: Commit transaction into InvoiceModel.
        @return: A String, representing the current InvoiceModel instance Document Number.
        """
        if self.can_generate_po_number():
            with transaction.atomic():

                EntityStateModel = lazy_loader.get_entity_state_model()

                try:
                    LOOKUP = {
                        'entity_id__exact': self.entity_id,
                        'entity_unit_id': None,
                        'fiscal_year__in': [self.date_draft.year, self.date_draft.year - 1],
                        'key__exact': EntityStateModel.KEY_PURCHASE_ORDER
                    }

                    state_model_qs = EntityStateModel.objects.select_related(
                        'entity').filter(**LOOKUP).annotate(
                        is_previous_fy=Case(
                            When(entity__fy_start_month__lt=self.date_draft.month,
                                 then=Value(0)),
                            default=Value(-1)
                        ),
                        fy_you_need=ExpressionWrapper(
                            Value(self.date_draft.year), output_field=IntegerField()
                        ) + F('is_previous_fy')).filter(
                        fiscal_year=F('fy_you_need')
                    )

                    state_model = state_model_qs.get()
                    state_model.sequence += 1
                    state_model.save(update_fields=['sequence'])

                except ObjectDoesNotExist:
                    EntityModel = lazy_loader.get_entity_model()
                    entity_model = EntityModel.objects.get(uuid__exact=self.entity_id)
                    fy_key = entity_model.get_fy_for_date(dt=self.date_draft)

                    LOOKUP = {
                        'entity_id': entity_model.uuid,
                        'entity_unit_id': None,
                        'fiscal_year': fy_key,
                        'key': EntityStateModel.KEY_PURCHASE_ORDER,
                        'sequence': 1
                    }
                    state_model = EntityStateModel(**LOOKUP)
                    state_model.clean()
                    state_model.save()

            seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
            self.po_number = f'{DJANGO_LEDGER_PO_NUMBER_PREFIX}-{state_model.fiscal_year}-{seq}'

            if commit:
                self.save(update_fields=['po_number'])

        return self.po_number

    def clean(self):
        if self.can_generate_po_number():
            self.generate_po_number(commit=False)

    def save(self, **kwargs):
        if self.can_generate_po_number():
            self.generate_po_number(commit=False)
        super(PurchaseOrderModelAbstract, self).save(**kwargs)


class PurchaseOrderModel(PurchaseOrderModelAbstract):
    """
    Purchase Order Base Model
    """
