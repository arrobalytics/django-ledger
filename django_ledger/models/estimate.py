"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from datetime import date
from decimal import Decimal
from string import ascii_uppercase, digits
from typing import Union
from uuid import uuid4, UUID

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator, MinLengthValidator
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Sum, Count, ExpressionWrapper, FloatField, F
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.models import (CreateUpdateMixIn, EntityModel, MarkdownNotesMixIn,
                                  CustomerModel, lazy_loader)
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_ESTIMATE_NUMBER_PREFIX

ESTIMATE_NUMBER_CHARS = ascii_uppercase + digits


class EstimateModelQuerySet(models.QuerySet):
    """
    A custom defined Query Set for the Estimate Model.
    This implements multiple methods or queries that we need to run to get a status of estimates.
    For e.g : We might want to have list of estimates which are Approved or  In draft stage.
    All these separate functions will assist in making such queries and building customized reports.
    """

    def approved(self):
        return self.filter(
            Q(status__exact=EstimateModelAbstract.CJ_STATUS_APPROVED) |
            Q(status__exact=EstimateModelAbstract.CJ_STATUS_COMPLETED)
        )

    def not_approved(self):
        return self.exclude(
            Q(status__exact=EstimateModelAbstract.CJ_STATUS_APPROVED) |
            Q(status__exact=EstimateModelAbstract.CJ_STATUS_COMPLETED)
        )

    def contracts(self):
        return self.approved()

    def estimates(self):
        return self.not_approved()


class EstimateModelManager(models.Manager):
    """
    A custom defined Estimate Model Manager that will act as an interface to handling the DB queries to the Estimate
    Model. The default "get_queryset" has been overridden to refer the custom defined "EstimateModelQuerySet"

    """

    def get_queryset(self):
        return EstimateModelQuerySet(self.model, using=self._db)

    def for_entity(self, entity_slug: Union[EntityModel, str], user_model):
        qs = self.get_queryset()
        if isinstance(entity_slug, EntityModel):
            return qs.filter(
                Q(entity=entity_slug) & (
                        Q(entity__admin=user_model) |
                        Q(entity__managers__in=[user_model])
                )
            )
        elif isinstance(entity_slug, str):
            return qs.filter(
                Q(entity__slug__exact=entity_slug) & (
                        Q(entity__admin=user_model) |
                        Q(entity__managers__in=[user_model])
                )
            )


class EstimateModelAbstract(CreateUpdateMixIn, MarkdownNotesMixIn):
    """
    This is the main abstract class which the Estimate Model database will inherit, and it contains the fields/columns/attributes which the said table will have.
    In addition to the attributes mentioned below, it also has the the fields/columns/attributes mentioned in below MixIn:
    
    MarkdownNotesMixIn
    CreateUpdateMixIn
    
    Read about these mixin here.

    Below are the fields specific to the bill model.
    @uuid : this is a unique primary key generated for the table. the default value of this fields is set as the unique uuid generated.
    @estimate_number: This is a slug  Field and hence a random estimate number with Max Length of 20 will be defined
    @entity: This is a slug  Field and hence a random bill number with Max Length of 20 will be defined
    @customer:  Aforeign Key reference from the Customer Model
    @terms: The value is among the choice from the Contract terms



    """

    CJ_STATUS_DRAFT = 'draft'
    CJ_STATUS_REVIEW = 'in_review'
    CJ_STATUS_APPROVED = 'approved'
    CJ_STATUS_COMPLETED = 'completed'
    CJ_STATUS_VOID = 'void'
    CJ_STATUS_CANCELED = 'canceled'
    CJ_STATUS = [
        (CJ_STATUS_DRAFT, _('Draft')),
        (CJ_STATUS_REVIEW, _('In Review')),
        (CJ_STATUS_APPROVED, _('Approved')),
        (CJ_STATUS_COMPLETED, _('Completed')),
        (CJ_STATUS_VOID, _('Void')),
        (CJ_STATUS_CANCELED, _('Canceled')),
    ]

    CJ_TERMS_FIXED = 'fixed'
    CJ_TERMS_TARGET_PRICE = 'target'
    CJ_TERMS_TM = 't&m'
    CJ_TERMS_OTHER = 'other'
    CONTRACT_TERMS = [
        (CJ_TERMS_FIXED, _('Fixed Price')),
        (CJ_TERMS_TARGET_PRICE, _('Target Price')),
        (CJ_TERMS_TM, _('Time & Materials')),
        (CJ_TERMS_OTHER, _('Other'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    estimate_number = models.SlugField(max_length=20,
                                       editable=False,
                                       verbose_name=_('Estimate Number'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('Entity Model'))
    customer = models.ForeignKey('django_ledger.CustomerModel', on_delete=models.RESTRICT, verbose_name=_('Customer'))
    terms = models.CharField(max_length=10, choices=CONTRACT_TERMS, verbose_name=_('Contract Terms'))
    title = models.CharField(max_length=250,
                             verbose_name=_('Customer Estimate Title'),
                             validators=[
                                 MinLengthValidator(limit_value=5,
                                                    message=_(f'PO Title length must be greater than 5'))
                             ])
    status = models.CharField(max_length=10,
                              choices=CJ_STATUS,
                              verbose_name=_('Customer Estimate Status'),
                              default=CJ_STATUS_DRAFT)

    date_draft = models.DateField(null=True, blank=True, verbose_name=_('Date Draft'))
    date_in_review = models.DateField(null=True, blank=True, verbose_name=_('Date In Review'))
    date_approved = models.DateField(null=True, blank=True, verbose_name=_('Date Approved'))
    date_completed = models.DateField(null=True, blank=True, verbose_name=_('Date Completed'))
    date_canceled = models.DateField(null=True, blank=True, verbose_name=_('Date Canceled'))
    date_void = models.DateField(null=True, blank=True, verbose_name=_('Date Void'))

    revenue_estimate = models.DecimalField(decimal_places=2,
                                           max_digits=20,
                                           default=Decimal('0.00'),
                                           verbose_name=_('Total revenue estimate'),
                                           help_text=_('Estimated cost to complete the quoted work.'),
                                           validators=[MinValueValidator(0)])

    labor_estimate = models.DecimalField(decimal_places=2,
                                         max_digits=20,
                                         default=Decimal('0.00'),
                                         verbose_name=_('Labor Cost of labor estimate'),
                                         help_text=_('Estimated labor cost to complete the quoted work.'),
                                         validators=[MinValueValidator(0)])

    material_estimate = models.DecimalField(decimal_places=2,
                                            max_digits=20,
                                            default=0.0,
                                            verbose_name=_('Material Cost Estimate'),
                                            help_text=_('Estimated material cost to complete the quoted work.'),
                                            validators=[MinValueValidator(0)])

    equipment_estimate = models.DecimalField(decimal_places=2,
                                             max_digits=20,
                                             default=Decimal('0.00'),
                                             verbose_name=_('Equipment Cost Estimate'),
                                             help_text=_('Estimated equipment cost to complete the quoted work.'),
                                             validators=[MinValueValidator(0)])

    other_estimate = models.DecimalField(decimal_places=2,
                                         max_digits=20,
                                         default=Decimal('0.00'),
                                         verbose_name=_('Other Cost Estimate'),
                                         help_text=_('Estimated equipment cost to complete the quoted work.'),
                                         validators=[MinValueValidator(0)])

    objects = EstimateModelManager()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _('Customer Job')
        verbose_name_plural = _('Customer Jobs')
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['customer']),
            models.Index(fields=['terms']),
            models.Index(fields=['entity']),

            models.Index(fields=['date_draft']),
            models.Index(fields=['date_in_review']),
            models.Index(fields=['date_approved']),
            models.Index(fields=['date_canceled']),
            models.Index(fields=['date_void']),
            models.Index(fields=['estimate_number']),
        ]
        unique_together = [
            ('entity', 'estimate_number')
        ]

    def __str__(self):
        if self.is_contract():
            return f'Contract {self.estimate_number} | {self.title}'
        return f'Estimate {self.estimate_number} | {self.title}'

    # Configuration...
    def configure(self,
                  entity_slug: Union[EntityModel, UUID, str],
                  user_model,
                  customer_model: CustomerModel,
                  commit: bool = False):
        if isinstance(entity_slug, str):
            entity_qs = EntityModel.objects.for_user(user_model=user_model)
            entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')
        self.entity = entity_model
        self.customer = customer_model
        if commit:
            self.save()
        return self

    # State....
    def is_draft(self):
        return self.status == self.CJ_STATUS_DRAFT

    def is_review(self):
        return self.status == self.CJ_STATUS_REVIEW

    def is_approved(self):
        return self.status == self.CJ_STATUS_APPROVED

    def is_completed(self):
        return self.status == self.CJ_STATUS_COMPLETED

    def is_canceled(self):
        return self.status == self.CJ_STATUS_CANCELED

    def is_void(self):
        return self.status == self.CJ_STATUS_VOID

    def is_contract(self):
        return any([
            self.is_approved(),
            self.is_completed()
        ])

    # Permissions...
    def can_draft(self):
        return self.is_review()

    def can_review(self):
        return self.is_draft()

    def can_approve(self):
        return self.is_review()

    def can_complete(self):
        return self.is_approved()

    def can_cancel(self):
        return any([
            self.is_draft(),
            self.is_review()
        ])

    def can_void(self):
        return self.is_approved()

    def can_update_items(self):
        return self.is_draft()

    def can_bind(self):
        return self.is_approved()

    def can_generate_estimate_number(self):
        return all([
            self.date_draft,
            self.entity_id,
            not self.estimate_number
        ])

    # Actions...
    # DRAFT...
    def mark_as_draft(self, commit: bool = False):
        if not self.can_draft():
            raise ValidationError(f'Estimate {self.estimate_number} cannot be marked as draft...')
        self.status = self.CJ_STATUS_DRAFT
        self.clean()
        if commit:
            self.save(update_fields=[
                'status',
                'updated'
            ])

    def get_mark_as_draft_html_id(self):
        return f'djl-{self.uuid}-estimate-mark-as-draft'

    def get_mark_as_draft_url(self):
        return reverse('django_ledger:customer-estimate-action-mark-as-draft',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ce_pk': self.uuid
                       })

    def get_mark_as_draft_message(self):
        return _('Do you want to mark Estimate %s as Draft?') % self.estimate_number

    # REVIEW...
    def mark_as_review(self, date_in_review: date = None, commit: bool = True):
        if not self.can_review():
            raise ValidationError(f'Estimate {self.estimate_number} cannot be marked as In Review...')

        itemtxs_qs = self.itemtransactionmodel_set.all()
        if not itemtxs_qs.count():
            raise ValidationError(message='Cannot review an Estimate without items...')
        if not self.get_cost_estimate():
            raise ValidationError(message='Cost amount is zero!.')
        if not self.revenue_estimate:
            raise ValidationError(message='Revenue amount is zero!.')

        if not date_in_review:
            date_in_review = localdate()
        self.date_in_review = date_in_review
        self.status = self.CJ_STATUS_REVIEW
        self.clean()
        if commit:
            self.save(update_fields=[
                'date_in_review',
                'status',
                'updated'
            ])

    def get_mark_as_review_html_id(self):
        return f'djl-{self.uuid}-estimate-mark-as-review'

    def get_mark_as_review_url(self):
        return reverse('django_ledger:customer-estimate-action-mark-as-review',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ce_pk': self.uuid
                       })

    def get_mark_as_review_message(self):
        return _('Do you want to mark Estimate %s as In Review?') % self.estimate_number

    def mark_as_approved(self, commit=False, date_approved: date = None) -> bool:
        if not self.can_approve():
            raise ValidationError(
                f'Estimate {self.estimate_number} cannot be marked as approved.'
            )
        if not date_approved:
            date_approved = localdate()
        self.date_approved = date_approved
        self.status = self.CJ_STATUS_APPROVED
        self.clean()
        if commit:
            self.save(update_fields=[
                'status',
                'date_approved',
                'updated'
            ])

    def get_mark_as_approved_html_id(self):
        return f'djl-{self.uuid}-estimate-mark-as-approved'

    def get_mark_as_approved_url(self):
        return reverse('django_ledger:customer-estimate-action-mark-as-approved',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ce_pk': self.uuid
                       })

    def get_mark_as_approved_message(self):
        return _('Do you want to mark Estimate %s as Approved?') % self.estimate_number

    # COMPLETED
    def mark_as_completed(self, commit=False, date_completed: date = None):

        if not self.can_complete():
            f'Estimate {self.estimate_number} cannot be marked as completed.'
        if not date_completed:
            date_completed = localdate()
        self.date_completed = date_completed
        self.status = self.CJ_STATUS_COMPLETED
        self.clean()
        if commit:
            self.clean()
            self.save(update_fields=[
                'status',
                'date_completed',
                'updated'
            ])

    def get_mark_as_completed_html_id(self):
        return f'djl-{self.uuid}-estimate-mark-as-completed'

    def get_mark_as_completed_url(self):
        return reverse('django_ledger:customer-estimate-action-mark-as-completed',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ce_pk': self.uuid
                       })

    def get_mark_as_completed_message(self):
        return _('Do you want to mark Estimate %s as Completed?') % self.estimate_number

    # CANCEL
    def mark_as_canceled(self, commit: bool = False, date_canceled: date = None):
        if not self.can_cancel():
            raise ValidationError(f'Estimate {self.estimate_number} cannot be canceled...')
        if not date_canceled:
            date_canceled = localdate()
        self.date_canceled = date_canceled
        self.status = self.CJ_STATUS_CANCELED
        self.clean()
        if commit:
            self.save(update_fields=[
                'status',
                'date_canceled',
                'updated'
            ])

    def get_mark_as_canceled_html_id(self):
        return f'djl-{self.uuid}-estimate-mark-as-canceled'

    def get_mark_as_canceled_url(self):
        return reverse('django_ledger:customer-estimate-action-mark-as-canceled',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ce_pk': self.uuid
                       })

    def get_mark_as_canceled_message(self):
        return _('Do you want to mark Estimate %s as Canceled?') % self.estimate_number

    # VOID
    def mark_as_void(self, commit: bool = False, date_void: date = None):
        if not self.can_void():
            raise ValidationError(f'Estimate {self.estimate_number} cannot be void...')
        if not date_void:
            date_void = localdate()
        self.date_void = date_void
        self.status = self.CJ_STATUS_VOID
        self.clean()
        if commit:
            self.save(update_fields=[
                'status',
                'date_void',
                'updated'
            ])

    def get_mark_as_void_html_id(self):
        return f'djl-{self.uuid}-estimate-mark-as-void'

    def get_mark_as_void_url(self):
        return reverse('django_ledger:customer-estimate-action-mark-as-void',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ce_pk': self.uuid
                       })

    def get_mark_as_void_message(self):
        return _('Do you want to mark Estimate %s as Void?') % self.estimate_number

    # HTML Tags...
    def get_html_id(self):
        return f'djl-customer-estimate-id-{self.uuid}'

    # ItemThroughModels...
    def get_itemtransaction_data(self, queryset=None) -> tuple:
        """
        Returns all ItemThroughModel associated with EstimateModel and a total aggregate.
        @param queryset: ItemThrough Queryset to use. If None a new queryset will be evaluated.
        @return: Tuple of ItemThroughModel Queryset and Aggregate.
        """
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemtransactionmodel_set.select_related('item_model').all()
        return queryset, queryset.aggregate(
            Sum('ce_cost_estimate'),
            Sum('ce_revenue_estimate'),
            total_items=Count('uuid')
        )

    def get_itemtxs_aggregate(self, queryset=None):
        """
        Returns all ItemThroughModel associated with EstimateModel and a total aggregate by ItemModel.
        @param queryset: ItemThrough Queryset to use. If None a new queryset will be evaluated.
        @return: Tuple of ItemThroughModel Queryset and Aggregate.
        """
        queryset, _ = self.get_itemtransaction_data(queryset)
        return queryset, queryset.values(
            'item_model_id', 'item_model__name'
        ).annotate(
            Sum('ce_quantity'),
            Sum('ce_cost_estimate'),
            Sum('ce_revenue_estimate'),
            avg_unit_cost=ExpressionWrapper(
                expression=Sum('ce_cost_estimate') / Sum('ce_quantity'),
                output_field=FloatField()
            ),
            avg_unit_revenue=ExpressionWrapper(
                expression=Sum('ce_revenue_estimate') / Sum('ce_quantity'),
                output_field=FloatField()
            )
        )

    def update_revenue_estimate(self, queryset):
        self.revenue_estimate = sum(i.ce_revenue_estimate for i in queryset)

    def update_cost_estimate(self, queryset):
        estimates = {
            'labor': sum(a.ce_cost_estimate for a in queryset if a.item_model.is_labor()),
            'material': sum(a.ce_cost_estimate for a in queryset if a.item_model.is_material()),
            'equipment': sum(a.ce_cost_estimate for a in queryset if a.item_model.is_equipment()),
            'other': sum(
                a.ce_cost_estimate for a in queryset
                if
                a.item_model.is_other() or not a.item_model_id or not a.item_model.item_type or a.item_model.is_lump_sum()
            ),
        }
        self.labor_estimate = estimates['labor']
        self.material_estimate = estimates['material']
        self.equipment_estimate = estimates['equipment']
        self.other_estimate = estimates['other']

    def update_state(self, queryset=None):
        if not queryset:
            queryset, _ = self.get_itemtransaction_data()
        self.update_cost_estimate(queryset)
        self.update_revenue_estimate(queryset)

    # Features...
    def get_cost_estimate(self, as_float: bool = False):
        estimate = sum([
            self.labor_estimate,
            self.material_estimate,
            self.equipment_estimate,
            self.other_estimate
        ])
        if as_float:
            return float(estimate)
        return estimate

    def get_revenue_estimate(self, as_float: bool = False):
        if as_float:
            return float(self.revenue_estimate)
        return self.revenue_estimate

    def profit_estimate(self):
        return self.revenue_estimate - self.get_cost_estimate()

    def gross_margin_estimate(self, as_percent: bool = False) -> float:
        try:
            gm = float(self.revenue_estimate) / float(self.get_cost_estimate()) - 1.00
            if as_percent:
                return gm * 100
            return gm
        except ZeroDivisionError:
            return 0.00

    def gross_margin_percent_estimate(self) -> float:
        return self.gross_margin_estimate(as_percent=True)

    def get_status_action_date(self):
        return getattr(self, f'date_{self.status}')

    # --- CONTRACT METHODS ---
    def get_po_amount(self, po_qs=None) -> dict:
        if not po_qs:
            PurchaseOrderModel = lazy_loader.get_purchase_order_model()
            po_qs = self.purchaseordermodel_set.all().active()
        return po_qs.aggregate(
            po_amount__sum=Coalesce(Sum('po_amount'), 0.0,
                                    output_field=models.FloatField())
        )

    def get_billed_amount(self, bill_qs=None) -> dict:
        if not bill_qs:
            BillModel = lazy_loader.get_bill_model()
            bill_qs = self.billmodel_set.all().active()
        return bill_qs.aggregate(
            bill_amount_due__sum=Coalesce(Sum('amount_due'), 0.0, output_field=models.FloatField()),
            bill_amount_paid__sum=Coalesce(Sum('amount_paid'), 0.0, output_field=models.FloatField()),
            bill_amount_receivable__sum=Coalesce(Sum('amount_receivable'), 0.0, output_field=models.FloatField()),
            bill_amount_earned__sum=Coalesce(Sum('amount_earned'), 0.0, output_field=models.FloatField()),
            bill_amount_unearned__sum=Coalesce(Sum('amount_unearned'), 0.0, output_field=models.FloatField()),
        )

    def get_invoiced_amount(self, invoice_qs=None) -> dict:
        if not invoice_qs:
            InvoiceModel = lazy_loader.get_invoice_model()
            invoice_qs = self.invoicemodel_set.all().active()

        return invoice_qs.aggregate(
            invoice_amount_due__sum=Coalesce(Sum('amount_due'), 0.0, output_field=models.FloatField()),
            invoice_amount_paid__sum=Coalesce(Sum('amount_paid'), 0.0, output_field=models.FloatField()),
            invoice_amount_receivable__sum=Coalesce(Sum('amount_receivable'), 0.0, output_field=models.FloatField()),
            invoice_amount_earned__sum=Coalesce(Sum('amount_earned'), 0.0, output_field=models.FloatField()),
            invoice_amount_unearned__sum=Coalesce(Sum('amount_unearned'), 0.0, output_field=models.FloatField()),
        )

    def get_contract_summary(self, po_qs=None, bill_qs=None, invoice_qs=None) -> dict:
        """
        Returns an aggregate of all related ItemTransactionModels summarizing
        original contract amounts, amounts authorized, amounts billed and amount invoiced.
        @return: A dictionary of aggregated values.
        """
        stats = {
            'cost_estimate': self.get_cost_estimate(as_float=True),
            'revenue_estimate': self.get_revenue_estimate(as_float=True)
        }

        po_status = self.get_po_amount(po_qs)
        billing_status = self.get_billed_amount(bill_qs)
        invoice_status = self.get_invoiced_amount(invoice_qs)
        return stats | po_status | billing_status | invoice_status

    def get_contract_transactions(self, entity_slug, user_model):
        ItemTransactionModel = lazy_loader.get_item_transaction_model()
        return ItemTransactionModel.objects.for_contract(
            entity_slug=entity_slug,
            user_model=user_model,
            ce_pk=self.uuid
        )

    def _get_next_state_model(self, raise_exception: bool = True):
        EntityStateModel = lazy_loader.get_entity_state_model()
        EntityModel = lazy_loader.get_entity_model()
        entity_model = EntityModel.objects.get(uuid__exact=self.entity_id)
        fy_key = entity_model.get_fy_for_date(dt=self.date_draft)
        try:
            LOOKUP = {
                'entity_model_id__exact': self.entity_id,
                'entity_unit_id': None,
                'fiscal_year': fy_key,
                'key__exact': EntityStateModel.KEY_ESTIMATE
            }

            state_model_qs = EntityStateModel.objects.filter(**LOOKUP).select_related(
                'entity_model').select_for_update()
            state_model = state_model_qs.get()
            state_model.sequence = F('sequence') + 1
            state_model.save()
            state_model.refresh_from_db()
            return state_model
        except ObjectDoesNotExist:
            EntityModel = lazy_loader.get_entity_model()
            entity_model = EntityModel.objects.get(uuid__exact=self.entity_id)
            fy_key = entity_model.get_fy_for_date(dt=self.date_draft)

            LOOKUP = {
                'entity_model_id': entity_model.uuid,
                'entity_unit_id': None,
                'fiscal_year': fy_key,
                'key': EntityStateModel.KEY_ESTIMATE,
                'sequence': 1
            }

            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model
        except IntegrityError as e:
            if raise_exception:
                raise e

    def generate_estimate_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next PurchaseOrder document number available.
        @param commit: Commit transaction into InvoiceModel.
        @return: A String, representing the current InvoiceModel instance Document Number.
        """
        if self.can_generate_estimate_number():
            with transaction.atomic(durable=True):

                state_model = None
                while not state_model:
                    state_model = self._get_next_state_model(raise_exception=False)

                seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
                self.estimate_number = f'{DJANGO_LEDGER_ESTIMATE_NUMBER_PREFIX}-{state_model.fiscal_year}-{seq}'

                if commit:
                    self.save(update_fields=['estimate_number'])

        return self.estimate_number

    def clean(self):

        if not self.date_draft:
            self.date_draft = localdate()

        if self.can_generate_estimate_number():
            self.generate_estimate_number(commit=False)

        if self.is_approved() and not self.date_approved:
            self.date_approved = localdate()

        if self.is_completed() and not self.date_completed:
            self.date_completed = localdate()

        if self.is_canceled():
            self.date_approved = None
            self.date_completed = None

    def save(self, **kwargs):
        if self.can_generate_estimate_number():
            self.generate_estimate_number(commit=False)
        super(EstimateModelAbstract, self).save(**kwargs)


class EstimateModel(EstimateModelAbstract):
    """
    Base Estimate Model Class
    """
