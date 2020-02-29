from datetime import timedelta, datetime
from decimal import Decimal
from random import choice
from string import ascii_uppercase, digits

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _l

from django_ledger.io.roles import GROUP_INCOME, ASSET_CA_RECEIVABLES, ASSET_CA_CASH, LIABILITY_CL_ACC_PAYABLE
from django_ledger.models import EntityModel
from django_ledger.models.mixins.base import CreateUpdateMixIn, ProgressibleMixIn

INVOICE_NUMBER_CHARS = ascii_uppercase + digits


def generate_invoice_number(length=10):
    return ''.join(choice(INVOICE_NUMBER_CHARS) for _ in range(length))


class InvoiceModelManager(models.Manager):

    def for_user(self, user_model):
        return self.get_queryset().filter(
            Q(ledger__entity__admin=user_model) |
            Q(ledger__entity__managers__in=[user_model])
        )

    def on_entity(self, entity):
        if isinstance(entity, EntityModel):
            return self.get_queryset().filter(ledger__entity=entity)
        elif isinstance(entity, str):
            return self.get_queryset().filter(ledger__entity__slug__exact=entity)


class InvoiceModelAbstract(CreateUpdateMixIn,
                           ProgressibleMixIn):
    INVOICE_TERMS = [
        ('on_receipt', 'Due On Receipt'),
        ('net_30', 'Due in 30 Days'),
        ('net_60', 'Due in 60 Days'),
        ('net_90', 'Due in 90 Days'),
    ]

    invoice_number = models.SlugField(max_length=20, verbose_name=_l('Invoice Number'))
    date = models.DateField(verbose_name=_l('Invoice Date'))
    due_date = models.DateField(verbose_name=_l('Due Date'))
    terms = models.CharField(max_length=10, default='on_receipt',
                             choices=INVOICE_TERMS, verbose_name=_l('Invoice Terms'))

    amount_due = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_l('Amount Due'))
    amount_paid = models.DecimalField(default=0, max_digits=20, decimal_places=2, verbose_name=_l('Amount Paid'))
    amount_receivable = models.DecimalField(default=0, max_digits=20, decimal_places=2,
                                            verbose_name=_l('Amount Receivable'))
    amount_unearned = models.DecimalField(default=0, max_digits=20, decimal_places=2,
                                          verbose_name=_l('Amount Unearned'))
    amount_earned = models.DecimalField(default=0, max_digits=20, decimal_places=2, verbose_name=_l('Amount Earned'))

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
                                  on_delete=models.CASCADE)
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_l('Invoice Cash Account'),
                                     related_name='invoices_cash',
                                     limit_choices_to={
                                         'role': ASSET_CA_CASH,
                                     })
    receivable_account = models.ForeignKey('django_ledger.AccountModel',
                                           on_delete=models.CASCADE,
                                           verbose_name=_l('Invoice Receivable Account'),
                                           related_name='invoices_ar',
                                           limit_choices_to={
                                               'role': ASSET_CA_RECEIVABLES
                                           })
    payable_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.CASCADE,
                                        verbose_name=_l('Invoice Liability Account'),
                                        related_name='invoices_ap',
                                        limit_choices_to={
                                            'role': LIABILITY_CL_ACC_PAYABLE
                                        })
    income_account = models.ForeignKey('django_ledger.AccountModel',
                                       on_delete=models.CASCADE,
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

    def get_amount_earned(self):
        if self.progressible:
            amount_due = self.amount_due or 0
            return self.progress * amount_due
        else:
            return self.amount_paid or 0

    def get_amount_receivable(self):
        payments = self.amount_paid or 0
        if self.get_amount_earned() >= payments:
            return self.get_amount_earned() - payments
        else:
            return 0

    def get_amount_unearned(self):
        if self.progressible:
            if self.get_amount_earned() <= self.amount_paid:
                return self.amount_paid - self.get_amount_earned()
        return Decimal()

    def get_amount_open(self):
        if self.progressible:
            amount_due = self.amount_due or 0
            return amount_due - self.get_amount_earned()
        else:
            amount_due = self.amount_due or 0
            payments = self.amount_paid or 0
            return amount_due - payments

    def db_state(self):
        return getattr(self, 'DB_STATE')

    def new_state(self, commit: bool = False):
        state = {
            'amount_paid': self.amount_paid,
            'amount_receivable': self.get_amount_receivable(),
            'amount_unearned': self.get_amount_unearned(),
            'amount_earned': self.get_amount_earned()
        }
        if commit:
            self.update_model_state(state)
        return state

    def update_model_state(self, state: dict = None):
        if not state:
            state = self.new_state()
        self.amount_receivable = state['amount_receivable']
        self.amount_unearned = state['amount_unearned']
        self.amount_earned = state['amount_earned']

    def migrate_state(self):
        current = self.db_state()
        new = self.new_state(commit=True)
        diff = {
            'amount_paid': new['amount_paid'] - current['amount_paid'],
            'amount_receivable': new['amount_receivable'] - current['amount_receivable'],
            'amount_unearned': new['amount_unearned'] - current['amount_unearned'],
            'amount_earned': new['amount_earned'] - current['amount_earned']
        }
        if not all([
            bool(amount) for k, amount in diff.items()
        ]):
            je_txs = [
                {
                    'account_id': self.cash_account_id,
                    'tx_type': 'debit' if diff['amount_paid'] >= 0 else 'credit',
                    'amount': diff['amount_paid'],
                    'description': f'Invoice {self.invoice_number} cash account adjustment.'
                },
                {
                    'account_id': self.receivable_account_id,
                    'tx_type': 'debit' if diff['amount_receivable'] >= 0 else 'credit',
                    'amount': diff['amount_receivable'],
                    'description': f'Invoice {self.invoice_number} receivable account adjustment.'
                },
                {
                    'account_id': self.payable_account_id,
                    'tx_type': 'credit' if diff['amount_unearned'] >= 0 else 'debit',
                    'amount': diff['amount_unearned'],
                    'description': f'Invoice {self.invoice_number} payable account adjustment'
                },
                {
                    'account_id': self.income_account_id,
                    'tx_type': 'credit' if diff['amount_earned'] >= 0 else 'debit',
                    'amount': diff['amount_earned'],
                    'description': f'Invoice {self.invoice_number} earnings account adjustment'
                },
            ]
            self.ledger.create_je_acc_id(
                je_date=datetime.now().date(),
                je_txs=je_txs,
                je_activity='op',
                je_posted=True,
                je_desc=f'Invoice {self.invoice_number} IO migration '

            )
        else:
            print(f'Invoice {self.invoice_number} has no entries... {diff}')

    def clean(self):

        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()

        if not self.date:
            self.date = datetime.now().date()

        if self.progressible:
            if not self.progress:
                self.progress = 0

        if self.terms != 'on_receipt':
            self.due_date = self.date + timedelta(days=int(self.terms.split('_')[-1]))
        else:
            self.due_date = self.date

        if self.paid:
            self.progress = 1.0
            self.amount_paid = self.amount_due

            today = datetime.now().date()
            if not self.paid_date:
                self.paid_date = today
            if self.paid_date > today:
                raise ValidationError('Cannot pay invoice in the future.')
            if self.paid_date < self.date:
                raise ValidationError('Cannot pay invoice before invoice date.')

        else:
            self.paid_date = None

    def save(self, *args, **kwargs):
        self.clean()
        self.migrate_state()
        super().save(*args, **kwargs)
