"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from datetime import date
from decimal import Decimal
from random import choices
from string import ascii_uppercase, digits
from typing import Union
from uuid import uuid4, UUID

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MinLengthValidator
from django.db import models
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CreateUpdateMixIn, EntityModel, MarkdownNotesMixIn, ItemModel, CustomerModel

ESTIMATE_NUMBER_CHARS = ascii_uppercase + digits


def generate_estimate_number(length: int = 10, prefix: bool = True) -> str:
    """
    A function that generates a random bill identifier for new bill models.
    :param prefix:
    :param length: The length of the bill number.
    :return: A string representing a random bill identifier.
    """
    estimate_number = ''.join(choices(ESTIMATE_NUMBER_CHARS, k=length))
    if prefix:
        estimate_number = 'E-' + estimate_number
    return estimate_number


class EstimateModelManager(models.Manager):

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
                                       verbose_name=_('Estimate Number'),
                                       default=generate_estimate_number)
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
        ]
        unique_together = [
            ('entity', 'estimate_number')
        ]

    def __str__(self):
        return f'Customer Estimate: {self.estimate_number} | {self.title}'

    # Configuration...
    def configure(self,
                  entity_slug: Union[EntityModel, UUID, str],
                  user_model,
                  customer_model: CustomerModel):
        if isinstance(entity_slug, str):
            entity_qs = EntityModel.objects.for_user(user_model=user_model)
            entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')
        self.estimate_number = generate_estimate_number()
        self.entity = entity_model
        self.customer = customer_model
        if not self.estimate_number:
            self.estimate_number = generate_estimate_number()
        self.clean()
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

        itemthrough_qs = self.itemthroughmodel_set.all()
        if not itemthrough_qs.count():
            raise ValidationError(message='Cannot review an Estimate without items...')
        if not self.cost_estimate():
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

    # State Update....
    def get_itemthrough_data(self, queryset=None) -> tuple:
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemthroughmodel_set.select_related('item_model').all()
        return queryset, queryset.aggregate(
            cost_estimate=Sum('total_amount'),
            revenue_estimate=Sum('ce_revenue_estimate'),
            total_items=Count('uuid')
        )

    def update_revenue_estimate(self, queryset):
        self.revenue_estimate = sum(i.ce_revenue_estimate for i in queryset)

    def update_cost_estimate(self, queryset):
        estimates = {
            'labor': sum(a.total_amount for a in queryset if a.item_model.is_labor()),
            'material': sum(a.total_amount for a in queryset if a.item_model.is_material()),
            'equipment': sum(a.total_amount for a in queryset if a.item_model.is_equipment()),
            'other': sum(
                a.total_amount for a in queryset
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
            queryset, _ = self.get_itemthrough_data()
        self.update_cost_estimate(queryset)
        self.update_revenue_estimate(queryset)

    # Features...
    def cost_estimate(self):
        return sum([
            self.labor_estimate,
            self.material_estimate,
            self.equipment_estimate,
            self.other_estimate
        ])

    def profit_estimate(self):
        return self.revenue_estimate - self.cost_estimate()

    def gross_margin_estimate(self, as_percent: bool = False) -> float:
        try:
            gm = float(self.revenue_estimate) / float(self.cost_estimate()) - 1.00
            if as_percent:
                return gm * 100
            return gm
        except ZeroDivisionError:
            return 0.00

    def gross_margin_percent_estimate(self) -> float:
        return self.gross_margin_estimate(as_percent=True)

    def get_status_action_date(self):
        return getattr(self, f'date_{self.status}')

    def clean(self):

        if not self.estimate_number:
            self.estimate_number = generate_estimate_number()

        if self.is_approved() and not self.date_approved:
            self.date_approved = localdate()

        if self.is_completed() and not self.date_completed:
            self.date_completed = localdate()

        if self.is_canceled():
            self.date_approved = None
            self.date_completed = None


class EstimateModel(EstimateModelAbstract):
    """
    Base Estimate Model Class
    """
