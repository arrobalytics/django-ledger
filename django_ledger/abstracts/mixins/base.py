from datetime import datetime
from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _l


class SlugNameMixIn(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.slug


class CreateUpdateMixIn(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class LedgerPlugInMixIn(models.Model):
    BALANCE_TYPE = None
    REL_NAME_PREFIX = None

    TERMS = [
        ('on_receipt', 'Due On Receipt'),
        ('net_30', 'Due in 30 Days'),
        ('net_60', 'Due in 60 Days'),
        ('net_90', 'Due in 90 Days'),
    ]

    terms = models.CharField(max_length=10,
                             default='on_receipt',
                             choices=TERMS,
                             verbose_name=_l('Terms'))

    amount_due = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_l('Amount Due'))
    amount_paid = models.DecimalField(default=0, max_digits=20, decimal_places=2, verbose_name=_l('Amount Paid'))

    amount_receivable = models.DecimalField(default=0, max_digits=20, decimal_places=2,
                                            verbose_name=_l('Amount Receivable'))
    amount_unearned = models.DecimalField(default=0, max_digits=20, decimal_places=2,
                                          verbose_name=_l('Amount Unearned'))
    amount_earned = models.DecimalField(default=0, max_digits=20, decimal_places=2, verbose_name=_l('Amount Earned'))

    paid = models.BooleanField(default=False, verbose_name=_l('Paid'))
    paid_date = models.DateField(null=True, blank=True, verbose_name=_l('Paid Date'))
    date = models.DateField(verbose_name=_l('Date'))
    due_date = models.DateField(verbose_name=_l('Due Date'))

    progressible = models.BooleanField(default=False, verbose_name=_l('Progressible'))
    progress = models.DecimalField(default=0,
                                   verbose_name=_l('Progress Amount'),
                                   decimal_places=2,
                                   max_digits=3,
                                   validators=[
                                       MinValueValidator(limit_value=0),
                                       MaxValueValidator(limit_value=1)
                                   ])

    ledger = models.OneToOneField('django_ledger.LedgerModel',
                                  verbose_name=_l('Ledger'),
                                  on_delete=models.CASCADE)
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_l('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    receivable_account = models.ForeignKey('django_ledger.AccountModel',
                                           on_delete=models.CASCADE,
                                           verbose_name=_l('Receivable Account'),
                                           related_name=f'{REL_NAME_PREFIX}_receivable_account')
    payable_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.CASCADE,
                                        verbose_name=_l('Payable Account'),
                                        related_name=f'{REL_NAME_PREFIX}_payable_account')
    income_account = models.ForeignKey('django_ledger.AccountModel',
                                       on_delete=models.CASCADE,
                                       verbose_name=_l('Income Account'),
                                       related_name=f'{REL_NAME_PREFIX}_income_account')

    class Meta:
        abstract = True

    def get_progress(self):
        if self.BALANCE_TYPE == 'debit':
            return self.progress
        elif self.BALANCE_TYPE == 'credit':
            return 1 - self.progress

    def get_amount_earned(self):
        if self.progressible:
            amount_due = self.amount_due or 0
            return self.get_progress() * amount_due
        else:
            return self.amount_paid or 0

    def get_amount_receivable(self):
        payments = self.amount_paid or 0
        if self.get_amount_earned() >= payments:
            return self.get_amount_earned() - payments
        else:
            return 0

    def get_amount_payable(self):
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

    def migrate_state(self, user_model):

        txs_digest = self.ledger.digest(user_model=user_model,
                                        process_groups=False,
                                        process_roles=False,
                                        process_ratios=False)
        account_data = txs_digest['tx_digest']['accounts']

        db_amount_paid = next(
            iter(acc['balance'] for acc in account_data if acc['account_id'] == self.cash_account_id), Decimal(0)
        )
        db_amount_receivable = next(
            iter(acc['balance'] for acc in account_data if acc['account_id'] == self.receivable_account_id), Decimal(0)
        )
        db_amount_payable = next(
            iter(acc['balance'] for acc in account_data if acc['account_id'] == self.payable_account_id), Decimal(0)
        )
        db_amount_earned = next(
            iter(acc['balance'] for acc in account_data if acc['account_id'] == self.income_account_id), Decimal(0)
        )

        new = self.new_state(commit=True)

        diff = {
            'amount_paid': new['amount_paid'] - db_amount_paid,
            'amount_receivable': new['amount_receivable'] - db_amount_receivable,
            'amount_payable': new['amount_unearned'] - db_amount_payable,
            'amount_earned': new['amount_earned'] - db_amount_earned
        }

        cash_entry = {
            'account_id': self.cash_account_id,
            'tx_type': 'debit' if diff['amount_paid'] >= 0 else 'credit',
            'amount': abs(diff['amount_paid']),
            'description': f'Invoice {self.invoice_number} cash account adjustment.'
        }
        receivable_entry = {
            'account_id': self.receivable_account_id,
            'tx_type': 'debit' if diff['amount_receivable'] >= 0 else 'credit',
            'amount': abs(diff['amount_receivable']),
            'description': f'Invoice {self.invoice_number} receivable account adjustment.'
        }
        payable_entry = {
            'account_id': self.payable_account_id,
            'tx_type': 'credit' if diff['amount_payable'] >= 0 else 'debit',
            'amount': abs(diff['amount_payable']),
            'description': f'Invoice {self.invoice_number} payable account adjustment'
        }
        earnings_entry = {
            'account_id': self.income_account_id,
            'tx_type': 'credit' if diff['amount_earned'] >= 0 else 'debit',
            'amount': abs(diff['amount_earned']),
            'description': f'Invoice {self.invoice_number} earnings account adjustment'
        }

        je_txs = list()
        if cash_entry['amount'] != 0:
            je_txs.append(cash_entry)
        if receivable_entry['amount'] != 0:
            je_txs.append(receivable_entry)
        if payable_entry['amount'] != 0:
            je_txs.append(payable_entry)
        if earnings_entry['amount'] != 0:
            je_txs.append(earnings_entry)

        self.ledger.create_je_acc_id(
            je_date=datetime.now().date(),
            je_txs=je_txs,
            je_activity='op',
            je_posted=True,
            je_desc=f'Invoice {self.invoice_number} IO migration '

        )

    def new_state(self, commit: bool = False):
        new_state = {
            'amount_paid': self.amount_paid,
            'amount_receivable': self.get_amount_receivable(),
            'amount_unearned': self.get_amount_payable(),
            'amount_earned': self.get_amount_earned()
        }
        if commit:
            self.update_state(new_state)
        return new_state

    def update_state(self, state: dict = None):
        if not state:
            state = self.new_state()
        self.amount_receivable = state['amount_receivable']
        self.amount_unearned = state['amount_unearned']
        self.amount_earned = state['amount_earned']


class NameAddressMixIn(models.Model):
    bill_to = models.CharField(max_length=50, verbose_name=_l('Bill To Name'))
    address_1 = models.CharField(max_length=70, verbose_name=_l('Address Line 1'))
    address_2 = models.CharField(null=True, blank=True, max_length=70, verbose_name=_l('Address Line 2'))
    email = models.EmailField(null=True, blank=True, verbose_name=_l('Email'))
    website = models.URLField(null=True, blank=True, verbose_name=_l('Website'))
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name=_l('Phone Number'))

    class Meta:
        abstract = True
