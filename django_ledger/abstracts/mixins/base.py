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


class ProgressibleMixIn(models.Model):
    progressible = models.BooleanField(default=False, verbose_name=_l('Progressible'))
    progress = models.DecimalField(null=True, blank=True, verbose_name=_l('Progress Amount'),
                                   decimal_places=2,
                                   max_digits=3,
                                   validators=[
                                       MinValueValidator(limit_value=0),
                                       MaxValueValidator(limit_value=1)
                                   ])

    class Meta:
        abstract = True


class LedgerPlugInMixIn(models.Model):
    ledger = models.OneToOneField('django_ledger.LedgerModel',
                                  verbose_name=_l('Invoice Ledger'),
                                  on_delete=models.CASCADE)
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_l('Cash Account'),
                                     related_name='cash_account')
    receivable_account = models.ForeignKey('django_ledger.AccountModel',
                                           on_delete=models.CASCADE,
                                           verbose_name=_l('Receivable Account'),
                                           related_name='receivable_account')
    payable_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.CASCADE,
                                        verbose_name=_l('Liability Account'),
                                        related_name='payable_account')
    income_account = models.ForeignKey('django_ledger.AccountModel',
                                       on_delete=models.CASCADE,
                                       verbose_name=_l('Income Account'),
                                       related_name='income_account')

    class Meta:
        abstract = True

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
        db_amount_unearned = next(
            iter(acc['balance'] for acc in account_data if acc['account_id'] == self.payable_account_id), Decimal(0)
        )
        db_amount_earned = next(
            iter(acc['balance'] for acc in account_data if acc['account_id'] == self.income_account_id), Decimal(0)
        )

        new = self.new_state(commit=True)

        diff = {
            'amount_paid': new['amount_paid'] - db_amount_paid,
            'amount_receivable': new['amount_receivable'] - db_amount_receivable,
            'amount_unearned': new['amount_unearned'] - db_amount_unearned,
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
            'tx_type': 'credit' if diff['amount_unearned'] >= 0 else 'debit',
            'amount': abs(diff['amount_unearned']),
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
