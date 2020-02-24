from datetime import timedelta, datetime
from random import choice
from string import ascii_uppercase, digits

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _l

from django_ledger.io.roles import GROUP_INCOME, ASSET_CA_RECEIVABLES, ASSET_CA_CASH, LIABILITY_CL_ACC_PAYABLE
from django_ledger.models import EntityModel
from django_ledger.models.mixins.base import CreateUpdateMixIn, ProgressibleMixIn

INVOICE_NUMBER_CHARS = ascii_uppercase + digits


def generate_invoice_number(length=10):
    return ''.join(choice(INVOICE_NUMBER_CHARS) for _ in range(length))


class InvoiceModelManager(models.Manager):

    def on_entity(self, entity):
        if isinstance(entity, EntityModel):
            return self.get_queryset().filter(ledger__entity=entity)
        elif isinstance(entity, str):
            return self.get_queryset().filter(ledger__entity__slug__iexact=entity)


class InvoiceModelAbstract(CreateUpdateMixIn,
                           ProgressibleMixIn):
    INVOICE_TERMS = [
        ('on_receipt', 'Due On Receipt'),
        ('net_30', 'Due in 30 Days'),
        ('net_60', 'Due in 60 Days'),
        ('net_90', 'Due in 90 Days'),
    ]

    invoice_number = models.SlugField(max_length=20, verbose_name=_l('Bill Number'))
    date = models.DateField(verbose_name=_l('Bill Date'))
    due_date = models.DateField(verbose_name=_l('Due Date'))
    terms = models.CharField(max_length=10, default='on_receipt',
                             choices=INVOICE_TERMS, verbose_name=_l('Bill Terms'))
    amount_due = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_l('Amount Due'))
    payment_amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_l('Payments'))
    paid = models.BooleanField(default=False, verbose_name=_l('Invoice Paid'))
    paid_date = models.DateField(null=True, blank=True, verbose_name=_l('Paid Date'))

    bill_to = models.CharField(max_length=50, verbose_name=_l('Bill To Name'))
    address_1 = models.CharField(max_length=70, verbose_name=_l('Address Line 1'))
    address_2 = models.CharField(null=True, blank=True, max_length=70, verbose_name=_l('Address Line 2'))
    email = models.EmailField(null=True, blank=True, verbose_name=_l('Email'))
    website = models.URLField(null=True, blank=True, verbose_name=_l('Website'))
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name=_l('Phone Number'))

    ledger = models.OneToOneField('django_ledger.LedgerModel',
                                  verbose_name=_l('Invoice Ledger'),
                                  on_delete=models.PROTECT)
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.PROTECT,
                                     verbose_name=_l('Invoice Cash Account'),
                                     related_name='invoices_cash',
                                     limit_choices_to={
                                         'role': ASSET_CA_CASH
                                     })
    receivable_account = models.ForeignKey('django_ledger.AccountModel',
                                           on_delete=models.PROTECT,
                                           verbose_name=_l('Invoice Receivable Account'),
                                           related_name='invoices_ar',
                                           limit_choices_to={
                                               'role': ASSET_CA_RECEIVABLES
                                           })
    payable_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.PROTECT,
                                        verbose_name=_l('Invoice Receivable Account'),
                                        related_name='invoices_ap',
                                        limit_choices_to={
                                            'role': LIABILITY_CL_ACC_PAYABLE
                                        })
    income_account = models.ForeignKey('django_ledger.AccountModel',
                                       on_delete=models.PROTECT,
                                       verbose_name=_l('Invoice Income Account'),
                                       related_name='invoices_in',
                                       limit_choices_to={
                                           'role__in': GROUP_INCOME
                                       })

    objects = InvoiceModelManager()

    class Meta:
        abstract = True
        verbose_name = _l('Invoice')
        verbose_name_plural = _l('Invoices')

    def __str__(self):
        return self.invoice_number

    def get_list_url(self, entity_slug):
        return reverse('django_ledger:invoice-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })

    def get_absolute_url(self, entity_slug):
        return reverse('django_ledger:invoice-detail',
                       kwargs={
                           'entity_slug': entity_slug,
                           'invoice_slug': self.invoice_number
                       })

    def clean(self):

        if not self.date:
            raise ValidationError('Must provide invoice date')

        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()

        if self.progressible:
            if not self.progress:
                self.progress = 0

        if self.terms != 'on_receipt':
            self.due_date = self.date + timedelta(days=int(self.terms.split('_')[-1]))
        else:
            self.due_date = self.date

        if self.paid:
            self.progress = 1.0
            self.payment_amount = self.amount_due

            today = datetime.now().date()
            if not self.paid_date:
                self.paid_date = today
            if self.paid_date > today:
                raise ValidationError('Cannot pay invoice in the future.')
            if self.paid_date < self.date:
                raise ValidationError('Cannot pay invoice before invoice date.')

        else:
            self.paid_date = None

    def earnings(self):
        if self.progressible:
            amount_due = self.amount_due or 0
            return self.progress * amount_due
        else:
            return self.payment_amount or 0

    def receivable(self):
        payments = self.payment_amount or 0
        if self.earnings() >= payments:
            return self.earnings() - payments
        else:
            return 0

    def unearned_receivable(self):
        if self.progressible:
            payments = self.payment_amount or 0
            if self.earnings() <= payments:
                return payments - self.earnings()
            else:
                return 0
        else:
            return 0

    def open(self):
        if self.progressible:
            amount_due = self.amount_due or 0
            return amount_due - self.earnings()
        else:
            amount_due = self.amount_due or 0
            payments = self.payment_amount or 0
            return amount_due - payments
