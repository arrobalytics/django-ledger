"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from random import choices
from string import ascii_uppercase, digits
from uuid import uuid4

from django.db import models
from django.db.models import Q, Sum, Count
from django.db.models.signals import post_delete
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.models.entity import EntityModel
from django_ledger.models.mixins import CreateUpdateMixIn, AccruableItemMixIn, ItemTotalCostMixIn


class LazyLoader:
    TXS_MODEL = None

    def get_txs_model(self):
        if not self.TXS_MODEL:
            from django_ledger.models.transactions import TransactionModel
            self.TXS_MODEL = TransactionModel
        return self.TXS_MODEL


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


class InvoiceModelAbstract(AccruableItemMixIn, CreateUpdateMixIn):
    IS_DEBIT_BALANCE = True
    REL_NAME_PREFIX = 'invoice'

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    invoice_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Invoice Number'))
    customer = models.ForeignKey('django_ledger.CustomerModel',
                                 on_delete=models.PROTECT,
                                 verbose_name=_('Customer'),
                                 blank=True,
                                 null=True)

    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.PROTECT,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    receivable_account = models.ForeignKey('django_ledger.AccountModel',
                                           on_delete=models.PROTECT,
                                           verbose_name=_('Receivable Account'),
                                           related_name=f'{REL_NAME_PREFIX}_receivable_account')
    payable_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.PROTECT,
                                        verbose_name=_('Payable Account'),
                                        related_name=f'{REL_NAME_PREFIX}_payable_account')
    earnings_account = models.ForeignKey('django_ledger.AccountModel',
                                         on_delete=models.PROTECT,
                                         verbose_name=_('Earnings Account'),
                                         related_name=f'{REL_NAME_PREFIX}_earnings_account')

    additional_info = models.JSONField(default=dict, verbose_name=_('Invoice Additional Info'))
    invoice_items = models.ManyToManyField('django_ledger.ItemModel',
                                           through='django_ledger.InvoiceModelItemsThroughModel',
                                           verbose_name=_('Invoice Items'))

    objects = InvoiceModelManager()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        indexes = [
            models.Index(fields=['cash_account']),
            models.Index(fields=['receivable_account']),
            models.Index(fields=['payable_account']),
            models.Index(fields=['earnings_account']),
            models.Index(fields=['date']),
            models.Index(fields=['due_date']),
            models.Index(fields=['paid']),
        ]

    def __str__(self):
        return f'Invoice: {self.invoice_number}'

    def get_absolute_url(self):
        return reverse('django_ledger:bill-detail',
                       kwargs={
                           'entity_slug': self.ledger.entity.slug,
                           'bill_pk': self.uuid
                       })

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
        :return:
        """
        return f'Invoice {self.invoice_number} account adjustment.'

    def get_invoice_item_data(self, queryset=None) -> tuple:
        if not queryset:
            queryset = self.invoicemodelitemsthroughmodel_set.all()
        return queryset, queryset.aggregate(
            amount_due=Sum('total_amount'),
            total_items=Count('uuid')
        )

    def update_amount_due(self, queryset=None) -> dict:
        queryset, item_data = self.get_invoice_item_data(queryset=queryset)
        self.amount_due = item_data['amount_due']
        return item_data

    def clean(self):
        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()
        super().clean()


class InvoiceModel(InvoiceModelAbstract):
    """
    Base Invoice Model from Abstract.
    """


def invoicemodel_predelete(instance: InvoiceModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(receiver=invoicemodel_predelete, sender=InvoiceModel)


class InvoiceModelItemsThroughManager(models.Manager):

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__slug__exact=entity_slug) &
            Q(entity__admin=user_model) |
            Q(entity__managers__in=[user_model])
        )

    def for_invoice(self, entity_slug: str, invoice_pk, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(invoice__uuid__exact=invoice_pk)


class InvoiceModelItemsThroughModelAbstract(ItemTotalCostMixIn, CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    invoice_model = models.ForeignKey('django_ledger.InvoiceModel',
                                      on_delete=models.CASCADE,
                                      verbose_name=_('Invoice Model'))

    objects = InvoiceModelItemsThroughManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['invoice_model', 'item_model']),
            models.Index(fields=['item_model', 'invoice_model']),
        ]

    def html_id_total_amount(self):
        return f'invoice-item-total-{self.uuid}'

    def html_id_quantity(self):
        return f'invoice-item-quantity-{self.uuid}'

    def html_id_unit_cost(self):
        return f'invoice-item-unit-{self.uuid}'


class InvoiceModelItemsThroughModel(InvoiceModelItemsThroughModelAbstract):
    """
    Base Invoice Items M2M Relationship Model from Abstract.
    """
