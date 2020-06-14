from datetime import timedelta, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _l

from django_ledger.io.roles import (GROUP_INCOME, GROUP_EXPENSES,
                                    ASSET_CA_CASH, LIABILITY_CL_ACC_PAYABLE, ASSET_CA_RECEIVABLES)


class LazyLoader:
    ACCOUNT_MODEL = None

    def get_account_model(self):
        if not self.ACCOUNT_MODEL:
            from django_ledger.models.accounts import AccountModel
            self.ACCOUNT_MODEL = AccountModel
        return self.ACCOUNT_MODEL


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


class ProgressibleMixIn(models.Model):
    IS_DEBIT_BALANCE = None
    REL_NAME_PREFIX = None
    ALLOW_MIGRATE = True

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
    void = models.BooleanField(default=False, verbose_name=_l('Void'))
    void_date = models.DateField(null=True, blank=True, verbose_name=_l('Void Date'))

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
    earnings_account = models.ForeignKey('django_ledger.AccountModel',
                                         on_delete=models.CASCADE,
                                         verbose_name=_l('Income Account'),
                                         related_name=f'{REL_NAME_PREFIX}_income_account')

    class Meta:
        abstract = True

    def get_progress(self):
        return self.progress

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

    def get_amount_receivable(self):
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

    def get_amount_payable(self):
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
            ).get(id=account_id)
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
                    acc_digest: dict,
                    adjustment_amount: Decimal):

        if adjustment_amount:
            # todo: implement this as a standalone function???
            tx_types = {
                'ci': 'credit',
                'dd': 'credit',
                'cd': 'debit',
                'di': 'debit',
            }

            acc_bal_type = acc_digest['balance_type'][0]
            d_or_i = 'd' if adjustment_amount < 0 else 'i'
            return tx_types[acc_bal_type + d_or_i]
        return 'debit'

    def migrate_state(self, user_model, entity_slug: str, force_migrate: bool = False, commit: bool = True):
        if self.migrate_allowed() or force_migrate:
            txs_digest = self.ledger.digest(user_model=user_model,
                                            process_groups=False,
                                            process_roles=False,
                                            process_ratios=False)

            account_data = txs_digest['tx_digest']['accounts']
            cash_acc_db = next(
                iter(acc for acc in account_data if acc['account_id'] == self.cash_account_id), None
            )
            rcv_acc_db = next(
                iter(acc for acc in account_data if acc['account_id'] == self.receivable_account_id), None
            )
            pay_acc_db = next(
                iter(acc for acc in account_data if acc['account_id'] == self.payable_account_id), None
            )
            earn_acc_db = next(
                iter(acc for acc in account_data if acc['account_id'] == self.earnings_account_id), None
            )

            new_state = self.new_state(commit=True)

            diff = {
                'amount_paid': new_state['amount_paid'] - (cash_acc_db['balance'] if cash_acc_db else 0),
                'amount_receivable': new_state['amount_receivable'] - (rcv_acc_db['balance'] if rcv_acc_db else 0),
                'amount_payable': new_state['amount_unearned'] - (pay_acc_db['balance'] if pay_acc_db else 0),
                # todo: chunk this down and figure out a cleaner way to deal with the earnings account.
                # todo: absolute is used here because amount earned can come from an income account or expense account.
                'amount_earned': new_state['amount_earned'] - abs(earn_acc_db['balance'] if earn_acc_db else 0)
            }

            je_txs = list()

            # todo: there may be a more efficient way of pulling all missing balance_types al once instead of 1-by-1.

            if diff['amount_paid'] != 0:
                if not cash_acc_db:
                    cash_acc_db = self.get_account_bt(
                        account_id=self.cash_account_id,
                        entity_slug=entity_slug,
                        user_model=user_model
                    )
                cash_tx = {
                    'account_id': self.cash_account_id,
                    'tx_type': self.get_tx_type(acc_digest=cash_acc_db, adjustment_amount=diff['amount_paid']),
                    'amount': abs(diff['amount_paid']),
                    'description': self.get_migrate_state_desc()
                }
                je_txs.append(cash_tx)

            if diff['amount_receivable'] != 0:
                if not rcv_acc_db:
                    rcv_acc_db = self.get_account_bt(
                        account_id=self.receivable_account_id,
                        entity_slug=entity_slug,
                        user_model=user_model
                    )
                receivable_tx = {
                    'account_id': self.receivable_account_id,
                    'tx_type': self.get_tx_type(acc_digest=rcv_acc_db, adjustment_amount=diff['amount_receivable']),
                    'amount': abs(diff['amount_receivable']),
                    'description': self.get_migrate_state_desc()
                }
                je_txs.append(receivable_tx)

            if diff['amount_payable'] != 0:
                if not pay_acc_db:
                    pay_acc_db = self.get_account_bt(
                        account_id=self.payable_account_id,
                        entity_slug=entity_slug,
                        user_model=user_model
                    )

                payable_tx = {
                    'account_id': self.payable_account_id,
                    'tx_type': self.get_tx_type(acc_digest=pay_acc_db, adjustment_amount=diff['amount_payable']),
                    'amount': abs(diff['amount_payable']),
                    'description': self.get_migrate_state_desc()
                }
                je_txs.append(payable_tx)

            if diff['amount_earned'] != 0:
                if not earn_acc_db:
                    earn_acc_db = self.get_account_bt(
                        account_id=self.earnings_account_id,
                        entity_slug=entity_slug,
                        user_model=user_model
                    )
                earnings_tx = {
                    'account_id': self.earnings_account_id,
                    'tx_type': self.get_tx_type(acc_digest=earn_acc_db, adjustment_amount=diff['amount_earned']),
                    'amount': abs(diff['amount_earned']),
                    'description': self.get_migrate_state_desc()
                }
                je_txs.append(earnings_tx)

            if len(je_txs) > 0:
                self.ledger.create_je_acc_id(
                    je_date=datetime.now().date(),
                    je_txs=je_txs,
                    je_activity='op',
                    je_posted=True,
                    je_desc=self.get_migrate_state_desc()
                )
        else:
            pass
            # raise ValidationError(f'{self.REL_NAME_PREFIX.upper()} state migration not allowed')

    def new_state(self, commit: bool = False):
        new_state = {
            'amount_paid': self.get_amount_cash(),
            'amount_receivable': self.get_amount_receivable(),
            # todo: rename this to amount_payable for consistency with model field.
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

    def clean(self):

        # todo: add validation based on income or expense scope...
        if not self.date:
            self.date = datetime.now().date()
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

        if self.amount_paid == self.amount_due:
            self.paid = True
        elif self.amount_paid > self.amount_due:
            raise ValidationError(f'Amount paid {self.amount_paid} cannot exceed amount due {self.amount_due}')

        if self.paid:
            self.progress = Decimal(1.0)
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

        if not self.migrate_allowed():
            self.update_state()


class ContactInfoMixIn(models.Model):
    subject_name = models.CharField(max_length=50, verbose_name=_l('Subject Name'))
    address_1 = models.CharField(max_length=70, verbose_name=_l('Address Line 1'))
    address_2 = models.CharField(null=True, blank=True, max_length=70, verbose_name=_l('Address Line 2'))
    email = models.EmailField(null=True, blank=True, verbose_name=_l('Email'))
    website = models.URLField(null=True, blank=True, verbose_name=_l('Website'))
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name=_l('Phone Number'))

    class Meta:
        abstract = True
