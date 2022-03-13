"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from typing import Union
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MinLengthValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CreateUpdateMixIn, EntityModel, MarkdownNotesMixIn


class CustomerJobModelManager(models.Manager):

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


class CustomerJobModel(CreateUpdateMixIn, MarkdownNotesMixIn):
    CJ_STATUS_DRAFT = 'draft'
    CJ_STATUS_REVIEW = 'in_review'
    CJ_STATUS_APPROVED = 'approved'
    CJ_STATUS_COMPLETED = 'completed'
    CJ_STATUS_CANCELED = 'canceled'

    CJ_STATUS = [
        (CJ_STATUS_DRAFT, _('Draft')),
        (CJ_STATUS_REVIEW, _('In Review')),
        (CJ_STATUS_APPROVED, _('Approved')),
        (CJ_STATUS_COMPLETED, _('Completed')),
        (CJ_STATUS_CANCELED, _('Canceled')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.ForeignKey('django_ledger.EntityModel', on_delete=models.CASCADE, verbose_name=_('Entity Model'))
    customer = models.ForeignKey('django_ledger.CustomerModel', on_delete=models.PROTECT, verbose_name=_('Customer'))
    title = models.CharField(max_length=250,
                             verbose_name=_('Customer Job Title'),
                             validators=[
                                 MinLengthValidator(limit_value=5,
                                                    message=_(f'PO Title length must be greater than 5'))
                             ])
    status = models.CharField(max_length=10, choices=CJ_STATUS,
                              verbose_name=_('Customer Job Status'),
                              default=CJ_STATUS_DRAFT)
    date_approved = models.DateField(null=True, blank=True, verbose_name=_('Date Approved'))
    date_completed = models.DateField(null=True, blank=True, verbose_name=_('Date Completed'))
    revenue_estimate = models.DecimalField(decimal_places=2,
                                           max_digits=20,
                                           default=0.0,
                                           verbose_name=_('Total revenue estimate'),
                                           help_text=_('Estimated cost to complete the quoted work.'),
                                           validators=[MinValueValidator(0)])

    labor_estimate = models.DecimalField(decimal_places=2,
                                         max_digits=20,
                                         default=0.0,
                                         verbose_name=_('Cost of labor estimate'),
                                         help_text=_('Estimated cost to complete the quoted work.'),
                                         validators=[MinValueValidator(0)])

    material_estimate = models.DecimalField(decimal_places=2,
                                            max_digits=20,
                                            default=0.0,
                                            verbose_name=_('Cost Estimate'),
                                            help_text=_('Estimated cost to complete the quoted work.'),
                                            validators=[MinValueValidator(0)])

    equipment_estimate = models.DecimalField(decimal_places=2,
                                             max_digits=20,
                                             default=0.0,
                                             verbose_name=_('Cost Estimate'),
                                             help_text=_('Estimated cost to complete the quoted work.'),
                                             validators=[MinValueValidator(0)])

    objects = CustomerJobModelManager()

    class Meta:
        ordering = ['-updated']
        verbose_name = _('Customer Job')
        verbose_name_plural = _('Customer Jobs')
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['date_approved']),
            models.Index(fields=['date_completed'])
        ]

    def __str__(self):
        return f'Customer Job: {self.title}'

    def is_approved(self):
        return self.status in [self.CJ_STATUS_APPROVED, self.CJ_STATUS_COMPLETED]

    def is_completed(self):
        return self.status == self.CJ_STATUS_COMPLETED

    def cost_estimate(self):
        return sum([self.labor_estimate, self.material_estimate, self.equipment_estimate])

    def profit_estimate(self):
        return self.revenue_estimate - self.cost_estimate()

    def get_html_id(self):
        return f'djl-customer-job-id-{self.uuid}'

    def clean(self):
        if self.is_approved() and not self.date_approved:
            raise ValidationError(message='Must provide date_approved for Customer Job.')

        if self.is_completed() and not self.date_completed:
            raise ValidationError(message='Must provide date_completed for Customer Job.')
