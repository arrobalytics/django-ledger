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

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, Count
from django.db.models.signals import post_delete
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.models import LazyLoader
from django_ledger.models.entity import EntityModel
from django_ledger.models.mixins import CreateUpdateMixIn, LedgerPlugInMixIn, MarkdownNotesMixIn

UserModel = get_user_model()

lazy_loader = LazyLoader()

INVOICE_NUMBER_CHARS = ascii_uppercase + digits


def generate_invoice_number(length: int = 10, prefix: bool = True) -> str:
    """
    A function that generates a random bill identifier for new bill models.
    :param prefix:
    :param length: The length of the bill number.
    :return: A string representing a random bill identifier.
    """
    invoice_number = ''.join(choices(INVOICE_NUMBER_CHARS, k=length))
    if prefix:
        invoice_number = 'I-' + invoice_number
    return invoice_number


class InvoiceModelManager(models.Manager):

    def for_entity(self, entity_slug, user_model):
        qs = self.get_queryset().filter(
            Q(ledger__entity__admin=user_model) |
            Q(ledger__entity__managers__in=[user_model])
        )
        if isinstance(entity_slug, EntityModel):
            return qs.filter(ledger__entity=entity_slug)
        elif isinstance(entity_slug, str):
            return qs.filter(ledger__entity__slug__exact=entity_slug)

    def for_entity_unpaid(self, entity_slug, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(paid=False)


class InvoiceModelAbstract(LedgerPlugInMixIn,
                           MarkdownNotesMixIn,
                           CreateUpdateMixIn):
    IS_DEBIT_BALANCE = True
    REL_NAME_PREFIX = 'invoice'

    INVOICE_STATUS_DRAFT = 'draft'
    INVOICE_STATUS_REVIEW = 'in_review'
    INVOICE_STATUS_APPROVED = 'approved'
    INVOICE_STATUS_CANCELED = 'canceled'

    INVOICE_STATUS = [
        (INVOICE_STATUS_DRAFT, _('Draft')),
        (INVOICE_STATUS_REVIEW, _('In Review')),
        (INVOICE_STATUS_APPROVED, _('Approved')),
        (INVOICE_STATUS_CANCELED, _('Canceled'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    invoice_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Invoice Number'))
    invoice_status = models.CharField(max_length=10, choices=INVOICE_STATUS, default=INVOICE_STATUS[0][0],
                                      verbose_name=_('Invoice Status'))
    customer = models.ForeignKey('django_ledger.CustomerModel',
                                 on_delete=models.PROTECT,
                                 verbose_name=_('Customer'))

    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.PROTECT,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    prepaid_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.PROTECT,
                                        verbose_name=_('Prepaid Account'),
                                        related_name=f'{REL_NAME_PREFIX}_prepaid_account')
    unearned_account = models.ForeignKey('django_ledger.AccountModel',
                                         on_delete=models.PROTECT,
                                         verbose_name=_('Unearned Account'),
                                         related_name=f'{REL_NAME_PREFIX}_unearned_account')

    additional_info = models.JSONField(default=dict, verbose_name=_('Invoice Additional Info'))
    invoice_items = models.ManyToManyField('django_ledger.ItemModel',
                                           through='django_ledger.ItemThroughModel',
                                           through_fields=('invoice_model', 'item_model'),
                                           verbose_name=_('Invoice Items'))

    objects = InvoiceModelManager()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        indexes = [
            models.Index(fields=['cash_account']),
            models.Index(fields=['prepaid_account']),
            models.Index(fields=['unearned_account']),
            models.Index(fields=['date']),
            models.Index(fields=['due_date']),
            models.Index(fields=['paid']),
        ]

    def __str__(self):
        return f'Invoice: {self.invoice_number}'

    def configure(self,
                  entity_slug: str or EntityModel,
                  user_model: UserModel,
                  post_ledger: bool = False):

        if isinstance(entity_slug, str):
            entity_qs = EntityModel.objects.for_user(
                user_model=user_model)
            entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')

        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()

        LedgerModel = lazy_loader.get_ledger_model()

        ledger_model = LedgerModel.objects.create(
            entity=entity_model,
            posted=post_ledger,
            name=f'Invoice {self.invoice_number}',
        )
        ledger_model.clean()
        self.ledger = ledger_model
        return ledger_model, self

    def get_document_id(self):
        return self.invoice_number

    def get_html_id(self):
        return f'djl-{self.REL_NAME_PREFIX}-{self.uuid}'

    def get_html_form_name(self):
        return f'djl-form-{self.REL_NAME_PREFIX}-{self.uuid}'

    def get_mark_paid_url(self, entity_slug):
        return reverse('django_ledger:invoice-mark-paid',
                       kwargs={
                           'entity_slug': entity_slug,
                           'invoice_pk': self.uuid
                       })

    def get_migrate_state_desc(self):
        """
        Must be implemented.
        :return:
        """
        return f'Invoice {self.invoice_number} account adjustment.'

    def get_invoice_item_data(self, queryset=None) -> tuple:
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemthroughmodel_set.all().select_related('item_model')
        return queryset, queryset.aggregate(
            amount_due=Sum('total_amount'),
            total_items=Count('uuid')
        )

    def migrate_allowed(self) -> bool:
        return self.invoice_status == InvoiceModel.INVOICE_STATUS_APPROVED

    def get_item_data(self, entity_slug: str, queryset=None):
        if not queryset:
            # pylint: disable=no-member
            queryset = self.itemthroughmodel_set.all()
            queryset = queryset.filter(invoice_model__ledger__entity__slug__exact=entity_slug)
        return queryset.select_related('item_model').order_by('item_model__earnings_account__uuid',
                                                              'entity_unit__uuid',
                                                              'item_model__earnings_account__balance_type').values(
            'item_model__earnings_account__uuid',
            'item_model__earnings_account__balance_type',
            'item_model__cogs_account__uuid',
            'item_model__cogs_account__balance_type',
            'item_model__inventory_account__uuid',
            'item_model__inventory_account__balance_type',
            'item_model__inventory_received',
            'item_model__inventory_received_value',
            'entity_unit__slug',
            'entity_unit__uuid',
            'quantity',
            'total_amount').annotate(
            account_unit_total=Sum('total_amount'))

    def update_amount_due(self, queryset=None, item_list: list = None) -> None or tuple:
        if item_list:
            # self.amount_due = Decimal.from_float(round(sum(a.total_amount for a in item_list), 2))
            self.amount_due = sum(a.total_amount for a in item_list)
            return
        queryset, item_data = self.get_invoice_item_data(queryset=queryset)
        self.amount_due = item_data['amount_due']
        return queryset, item_data

    def is_approved(self):
        return self.invoice_status == self.INVOICE_STATUS_APPROVED

    def is_draft(self):
        return self.invoice_status == self.INVOICE_STATUS_DRAFT

    def can_edit_items(self):
        return self.is_draft()

    def can_update_items(self):
        return self.invoice_status not in [
            self.INVOICE_STATUS_APPROVED,
            self.INVOICE_STATUS_CANCELED
        ]

    def clean(self):
        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()
        if self.is_draft():
            self.amount_paid = Decimal('0.00')
            self.paid = False
            self.paid_date = None
            self.progress = 0
        super().clean()


class InvoiceModel(InvoiceModelAbstract):
    """
    Base Invoice Model from Abstract.
    """


def invoicemodel_predelete(instance: InvoiceModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(receiver=invoicemodel_predelete, sender=InvoiceModel)
