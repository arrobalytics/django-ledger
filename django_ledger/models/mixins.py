"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from datetime import timedelta
from decimal import Decimal
from itertools import groupby
from uuid import uuid4

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import QuerySet
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from django_ledger.io import validate_tx_data
from django_ledger.io.roles import (GROUP_INCOME, GROUP_EXPENSES,
                                    ASSET_CA_CASH, LIABILITY_CL_ACC_PAYABLE,
                                    ASSET_CA_RECEIVABLES)


class LazyLoader:
    ACCOUNT_MODEL = None
    BILL_MODEL = None
    JOURNAL_ENTRY_MODEL = None
    TXS_MODEL = None

    def get_account_model(self):
        if not self.ACCOUNT_MODEL:
            from django_ledger.models.accounts import AccountModel
            self.ACCOUNT_MODEL = AccountModel
        return self.ACCOUNT_MODEL

    def get_bill_model(self):
        if not self.BILL_MODEL:
            from django_ledger.models import BillModel
            self.BILL_MODEL = BillModel
        return self.BILL_MODEL

    def get_journal_entry_model(self):
        if not self.JOURNAL_ENTRY_MODEL:
            from django_ledger.models import JournalEntryModel
            self.JOURNAL_ENTRY_MODEL = JournalEntryModel
        return self.JOURNAL_ENTRY_MODEL

    def get_transaction_model(self):
        if not self.TXS_MODEL:
            from django_ledger.models import TransactionModel
            self.TXS_MODEL = TransactionModel
        return self.TXS_MODEL


lazy_loader = LazyLoader()


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


class ContactInfoMixIn(models.Model):
    address_1 = models.CharField(max_length=70, verbose_name=_('Address Line 1'))
    address_2 = models.CharField(null=True, blank=True, max_length=70, verbose_name=_('Address Line 2'))
    city = models.CharField(null=True, blank=True, max_length=70, verbose_name=_('City'))
    state = models.CharField(null=True, blank=True, max_length=70, verbose_name=_('State/Province'))
    zip_code = models.CharField(null=True, blank=True, max_length=20, verbose_name=_('Zip Code'))
    country = models.CharField(null=True, blank=True, max_length=70, verbose_name=_('Country'))
    email = models.EmailField(null=True, blank=True, verbose_name=_('Email'))
    website = models.URLField(null=True, blank=True, verbose_name=_('Website'))
    phone = models.CharField(max_length=30, null=True, blank=True, verbose_name=_('Phone Number'))

    class Meta:
        abstract = True

    def get_cszc(self):
        if all([
            self.city,
            self.state,
            self.zip_code,
            self.country,
        ]):
            return f'{self.city}, {self.state}. {self.zip_code}. {self.country}'


class AccruableItemMixIn(models.Model):
    IS_DEBIT_BALANCE = None
    REL_NAME_PREFIX = None
    ALLOW_MIGRATE = True

    TERMS = [
        ('on_receipt', 'Due On Receipt'),
        ('net_30', 'Net 30 Days'),
        ('net_60', 'Net 60 Days'),
        ('net_90', 'Net 90 Days'),
    ]

    terms = models.CharField(max_length=10,
                             default='on_receipt',
                             choices=TERMS,
                             verbose_name=_('Terms'))

    amount_due = models.DecimalField(default=0, max_digits=20, decimal_places=2, verbose_name=_('Amount Due'))
    amount_paid = models.DecimalField(default=0, max_digits=20, decimal_places=2, verbose_name=_('Amount Paid'))

    amount_receivable = models.DecimalField(default=0, max_digits=20, decimal_places=2,
                                            verbose_name=_('Amount Receivable'))
    amount_unearned = models.DecimalField(default=0, max_digits=20, decimal_places=2,
                                          verbose_name=_('Amount Unearned'))
    amount_earned = models.DecimalField(default=0, max_digits=20, decimal_places=2, verbose_name=_('Amount Earned'))

    paid = models.BooleanField(default=False, verbose_name=_('Paid'))
    paid_date = models.DateField(null=True, blank=True, verbose_name=_('Paid Date'))
    date = models.DateField(verbose_name=_('Date'))
    due_date = models.DateField(verbose_name=_('Due Date'))
    void = models.BooleanField(default=False, verbose_name=_('Void'))
    void_date = models.DateField(null=True, blank=True, verbose_name=_('Void Date'))

    progressible = models.BooleanField(default=False, verbose_name=_('Progressible'))
    progress = models.DecimalField(default=0,
                                   verbose_name=_('Progress Amount'),
                                   decimal_places=2,
                                   max_digits=3,
                                   validators=[
                                       MinValueValidator(limit_value=0),
                                       MaxValueValidator(limit_value=1)
                                   ])

    ledger = models.OneToOneField('django_ledger.LedgerModel',
                                  verbose_name=_('Ledger'),
                                  on_delete=models.CASCADE)
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    receivable_account = models.ForeignKey('django_ledger.AccountModel',
                                           on_delete=models.CASCADE,
                                           verbose_name=_('Receivable Account'),
                                           related_name=f'{REL_NAME_PREFIX}_receivable_account')
    payable_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.CASCADE,
                                        verbose_name=_('Payable Account'),
                                        related_name=f'{REL_NAME_PREFIX}_payable_account')
    earnings_account = models.ForeignKey('django_ledger.AccountModel',
                                         on_delete=models.CASCADE,
                                         verbose_name=_('Income Account'),
                                         related_name=f'{REL_NAME_PREFIX}_income_account')

    class Meta:
        abstract = True

    def get_progress(self):
        if self.progressible:
            return self.progress
        if not self.amount_due:
            return 0
        return (self.amount_paid or 0) / self.amount_due
        # return Decimal(round(((self.amount_paid or 0) / self.amount_due), 2))

    def get_progress_percent(self):
        return self.get_progress() * 100

    def get_amount_cash(self):
        if self.IS_DEBIT_BALANCE:
            return self.amount_paid
        elif not self.IS_DEBIT_BALANCE:
            return -self.amount_paid

    def get_amount_earned(self):
        if self.progressible:
            amount_due = self.amount_due or 0
            return self.get_progress() * amount_due
        else:
            return self.amount_paid or 0

    def get_amount_prepaid(self):
        payments = self.amount_paid or 0
        if self.progressible:
            amt_earned = self.get_amount_earned()
            if all([self.IS_DEBIT_BALANCE,
                    amt_earned >= payments]):
                return self.get_amount_earned() - payments
            elif all([not self.IS_DEBIT_BALANCE,
                      amt_earned <= payments]):
                return payments - self.get_amount_earned()
        return 0

    def get_amount_unearned(self):
        if self.progressible:
            amt_earned = self.get_amount_earned()
            if all([self.IS_DEBIT_BALANCE,
                    amt_earned <= self.amount_paid]):
                return self.amount_paid - amt_earned
            elif all([not self.IS_DEBIT_BALANCE,
                      amt_earned >= self.amount_paid]):
                return amt_earned - self.amount_paid
        return 0

    def get_amount_open(self):
        if self.progressible:
            amount_due = self.amount_due or 0
            return amount_due - self.get_amount_earned()
        else:
            amount_due = self.amount_due or 0
            payments = self.amount_paid or 0
            return amount_due - payments

    def get_account_bt(self, account_id, user_model, entity_slug: str):
        """
        Creates a dictionary that contains the balance_type parameter of an account for Migration in case there
        are no existing entries.
        :return:
        """
        AccountModel = lazy_loader.get_account_model()

        try:
            account = AccountModel.on_coa.for_entity_available(
                user_model=user_model,
                entity_slug=entity_slug
            ).get(uuid__exact=account_id)
        except ObjectDoesNotExist:
            raise ValidationError(f'Account ID: {account_id} may be locked or unavailable...')
        return {
            'balance_type': account.balance_type
        }

    def get_migrate_state_desc(self, *args, **kwargs):
        """
        Must be implemented.
        :return:
        """

    def migrate_allowed(self) -> bool:
        """
        Function returning if model state can be migrated to related accounts.
        :return:
        """
        return self.ALLOW_MIGRATE

    def get_tx_type(self,
                    acc_bal_type: dict,
                    adjustment_amount: Decimal):

        if adjustment_amount:
            # todo: implement this as a standalone function???
            tx_types = {
                'ci': 'credit',
                'dd': 'credit',
                'cd': 'debit',
                'di': 'debit',
            }

            acc_bal_type = acc_bal_type[0]
            d_or_i = 'd' if adjustment_amount < 0 else 'i'
            return tx_types[acc_bal_type + d_or_i]
        return 'debit'

    def split_amount(self, amount: float, unit_split: dict, account_uuid, account_balance_type) -> dict:
        running_alloc = 0
        SPLIT_LEN = len(unit_split) - 1
        split_results = dict()
        for i, (u, p) in enumerate(unit_split.items()):
            if i == SPLIT_LEN:
                split_results[(account_uuid, u, account_balance_type)] = amount - running_alloc
            else:
                alloc = round(p * amount, 2)
                split_results[(account_uuid, u, account_balance_type)] = alloc
                running_alloc += alloc
        return split_results

    def migrate_state(self,
                      user_model,
                      entity_slug: str,
                      item_models: QuerySet or list = None,
                      force_migrate: bool = False,
                      commit: bool = True,
                      je_date: date = None):

        if self.migrate_allowed() or force_migrate:
            txs_digest = self.ledger.digest(
                user_model=user_model,
                process_groups=True,
                process_roles=False,
                process_ratios=False,
                by_unit=True
            )

            digest_data = txs_digest['tx_digest']['accounts']

            ledger_state = {
                (a['account_uuid'], a['unit_uuid'], a['balance_type']): a['balance'] for a in digest_data
            }

            new_state = self.new_state(commit=commit)
            account_balance_data = self.get_account_balance_data()
            account_balance_data_gb = groupby(account_balance_data,
                                              key=lambda a: (a['item_model__expense_account__uuid'],
                                                             a['entity_unit__uuid'],
                                                             a['item_model__expense_account__balance_type']))
            progress = self.get_progress()
            account_balance_data_idx = {
                g: round(sum(a['account_unit_total'] for a in ad) * progress, 2) for g, ad in account_balance_data_gb
            }
            ua_gen = sorted(((k[1], v) for k, v in account_balance_data_idx.items()),
                            key=lambda a: a[0] if a[0] else uuid4())
            unit_amounts = {
                u: sum(a[1] for a in l) for u, l in groupby(ua_gen, key=lambda x: x[0])
            }
            total_amount = sum(unit_amounts.values())
            unit_percents = {
                k: (v / total_amount) for k, v in unit_amounts.items()
            }

            current_state = dict()
            current_state.update(self.split_amount(
                amount=new_state['amount_paid'],
                unit_split=unit_percents,
                account_uuid=self.cash_account_id,
                account_balance_type='debit'
            ))
            current_state.update(self.split_amount(
                amount=new_state['amount_receivable'],
                unit_split=unit_percents,
                account_uuid=self.receivable_account_id,
                account_balance_type='debit'
            ))
            current_state.update(self.split_amount(
                amount=new_state['amount_unearned'],
                unit_split=unit_percents,
                account_uuid=self.payable_account_id,
                account_balance_type='credit'
            ))
            current_state.update(account_balance_data_idx)

            idx_keys = set(list(ledger_state) + list(current_state))
            unit_uuids = list(set(k[1] for k in idx_keys))
            diff_idx = {
                k: current_state.get(k, 0) - ledger_state.get(k, 0) for k in idx_keys
            }

            JournalEntryModel = lazy_loader.get_journal_entry_model()
            TransactionModel = lazy_loader.get_transaction_model()

            now_date = localdate() if not je_date else je_date
            je_list = {
                u: JournalEntryModel.objects.create(
                    entity_unit_id=u,
                    date=now_date,
                    description=self.get_migrate_state_desc(),
                    activity='op',
                    origin='migration',
                    locked=True,
                    ledger_id=self.ledger_id
                ) for u in list(unit_uuids)
            }

            txs_list = [
                TransactionModel(
                    journal_entry=je_list.get(unit_uuid),
                    amount=abs(amt),
                    tx_type=self.get_tx_type(acc_bal_type=bal_type, adjustment_amount=amt),
                    account_id=acc_uuid,
                    description=self.get_migrate_state_desc()
                ) for (acc_uuid, unit_uuid, bal_type), amt in diff_idx.items() if amt
            ]

            for tx in txs_list:
                tx.full_clean()

            validate_tx_data(tx_data=txs_list)

            TransactionModel.objects.bulk_create(txs_list)

        else:
            raise ValidationError(f'{self.REL_NAME_PREFIX.upper()} state migration not allowed')

    def new_state(self, commit: bool = False):
        new_state = {
            'amount_paid': self.get_amount_cash(),
            'amount_receivable': self.get_amount_prepaid(),
            'amount_unearned': self.get_amount_unearned(),
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

    def due_in_days(self):
        td = self.due_date - localdate()
        if td.days < 0:
            return 0
        return td.days

    def is_past_due(self):
        return not self.paid if self.paid else self.due_date < localdate()

    def net_due_group(self):
        due_in = self.due_in_days()
        if due_in == 0:
            return 'net_0'
        elif due_in <= 30:
            return 'net_30'
        elif due_in <= 60:
            return 'net_60'
        elif due_in <= 90:
            return 'net_90'
        else:
            return 'net_90+'

    def clean(self):

        if not self.date:
            self.date = localdate()
        if self.cash_account.role != ASSET_CA_CASH:
            raise ValidationError(f'Cash account must be of role {ASSET_CA_CASH}')
        if self.receivable_account.role != ASSET_CA_RECEIVABLES:
            raise ValidationError(f'Receivable account must be of role {ASSET_CA_RECEIVABLES}')
        if self.payable_account.role != LIABILITY_CL_ACC_PAYABLE:
            raise ValidationError(f'Payable account must be of role {LIABILITY_CL_ACC_PAYABLE}')

        if all([
            self.IS_DEBIT_BALANCE,
            self.earnings_account.role not in GROUP_INCOME
        ]):
            raise ValidationError(f'Earnings account must be of role {GROUP_INCOME}')
        elif all([
            not self.IS_DEBIT_BALANCE,
            self.earnings_account.role not in GROUP_EXPENSES
        ]):
            raise ValidationError(f'Earnings account must be of role {GROUP_EXPENSES}')

        if self.progressible and self.progress is None:
            self.progress = 0

        if self.terms != 'on_receipt':
            self.due_date = self.date + timedelta(days=int(self.terms.split('_')[-1]))
        else:
            self.due_date = self.date

        if self.amount_due and self.amount_paid == self.amount_due:
            self.paid = True
        elif self.amount_paid > self.amount_due:
            raise ValidationError(f'Amount paid {self.amount_paid} cannot exceed amount due {self.amount_due}')

        if self.paid:
            self.progress = Decimal(1.0)
            self.amount_paid = self.amount_due
            today = localdate()

            if not self.paid_date:
                self.paid_date = today
            if self.paid_date > today:
                raise ValidationError('Cannot pay invoice in the future.')
            if self.paid_date < self.date:
                raise ValidationError('Cannot pay invoice before invoice date.')
        else:
            self.paid_date = None

        if self.migrate_allowed():
            self.update_state()


class ItemTotalCostMixIn(models.Model):
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel',
                                    on_delete=models.SET_NULL,
                                    blank=True,
                                    null=True,
                                    verbose_name=_('Associated Entity Unit'))
    item_model = models.ForeignKey('django_ledger.ItemModel',
                                   on_delete=models.PROTECT,
                                   verbose_name=_('Item Model'))
    quantity = models.FloatField(default=0.0,
                                 verbose_name=_('Quantity'),
                                 validators=[MinValueValidator(0)])
    unit_cost = models.FloatField(default=0.0,
                                  verbose_name=_('Cost Per Unit'),
                                  validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=20,
                                       editable=False,
                                       decimal_places=2,
                                       verbose_name=_('Total Amount QTY x UnitCost'),
                                       validators=[MinValueValidator(0)])

    class Meta:
        abstract = True

    def update_total_amount(self):
        self.total_amount = round(self.quantity * self.unit_cost, 2)

    def clean(self):
        self.update_total_amount()
