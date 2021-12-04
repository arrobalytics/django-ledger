"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from itertools import groupby

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import QuerySet
from django.utils.encoding import force_str
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from markdown import markdown

from django_ledger.io import balance_tx_data, ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_DEFERRED_REVENUE


class LazyLoader:
    # todo: find other implementations of Lazy Loaders and replace with this one...
    ACCOUNT_MODEL = None
    BILL_MODEL = None
    INVOICE_MODEL = None
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

    def get_invoice_model(self):
        if not self.INVOICE_MODEL:
            from django_ledger.models import InvoiceModel
            self.INVOICE_MODEL = InvoiceModel
        return self.INVOICE_MODEL

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
        # pylint: disable=invalid-str-returned
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


class LedgerPlugInMixIn(models.Model):
    IS_DEBIT_BALANCE = None
    REL_NAME_PREFIX = None
    ALLOW_MIGRATE = True
    TX_TYPE_MAPPING = {
        'ci': 'credit',
        'dd': 'credit',
        'cd': 'debit',
        'di': 'debit',
    }

    TERMS_ON_RECEIPT = 'on_receipt'
    TERMS_NET_30 = 'net_30'
    TERMS_NET_60 = 'net_60'
    TERMS_NET_90 = 'net_90'
    TERMS_NET_90_PLUS = 'net_90+'

    TERMS = [
        (TERMS_ON_RECEIPT, 'Due On Receipt'),
        (TERMS_NET_30, 'Net 30 Days'),
        (TERMS_NET_60, 'Net 60 Days'),
        (TERMS_NET_90, 'Net 90 Days'),
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

    accrue = models.BooleanField(default=False, verbose_name=_('Progressible'))

    # todo: change progress method from percent to currency amount...
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
                                     on_delete=models.PROTECT,
                                     blank=True,
                                     null=True,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    prepaid_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.PROTECT,
                                        blank=True,
                                        null=True,
                                        verbose_name=_('Prepaid Account'),
                                        related_name=f'{REL_NAME_PREFIX}_prepaid_account')
    unearned_account = models.ForeignKey('django_ledger.AccountModel',
                                         on_delete=models.PROTECT,
                                         blank=True,
                                         null=True,
                                         verbose_name=_('Unearned Account'),
                                         related_name=f'{REL_NAME_PREFIX}_unearned_account')

    class Meta:
        abstract = True

    def get_progress(self):
        if self.accrue:
            return self.progress
        if not self.amount_due:
            return 0
        return (self.amount_paid or 0) / self.amount_due

    def get_progress_percent(self):
        return round(self.get_progress() * 100, 2)

    def get_amount_cash(self):
        if self.IS_DEBIT_BALANCE:
            return self.amount_paid
        elif not self.IS_DEBIT_BALANCE:
            return -self.amount_paid

    def get_amount_earned(self):
        if self.accrue:
            amount_due = self.amount_due or 0
            return self.get_progress() * amount_due
        else:
            return self.amount_paid or 0

    def get_amount_prepaid(self):
        payments = self.amount_paid or 0
        if self.accrue:
            amt_earned = self.get_amount_earned()
            if all([self.IS_DEBIT_BALANCE,
                    amt_earned >= payments]):
                return self.get_amount_earned() - payments
            elif all([not self.IS_DEBIT_BALANCE,
                      amt_earned <= payments]):
                return payments - self.get_amount_earned()
        return 0

    def get_amount_unearned(self):
        if self.accrue:
            amt_earned = self.get_amount_earned()
            if all([self.IS_DEBIT_BALANCE,
                    amt_earned <= self.amount_paid]):
                return self.amount_paid - amt_earned
            elif all([not self.IS_DEBIT_BALANCE,
                      amt_earned >= self.amount_paid]):
                return amt_earned - self.amount_paid
        return 0

    def get_amount_open(self):
        if self.accrue:
            amount_due = self.amount_due or 0
            return amount_due - self.get_amount_earned()
        else:
            amount_due = self.amount_due or 0
            payments = self.amount_paid or 0
            return amount_due - payments

    def get_item_data(self, entity_slug: str, queryset=None):
        raise NotImplementedError('Must implement get_account_balance_data method.')

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
            acc_bal_type = acc_bal_type[0]
            d_or_i = 'd' if adjustment_amount < 0 else 'i'
            return self.TX_TYPE_MAPPING[acc_bal_type + d_or_i]
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

    def is_configured(self):
        return all([
            self.cash_account_id is not None,
            self.unearned_account_id is not None,
            self.prepaid_account_id is not None
        ])

    def mark_as_paid(self,
                     user_model,
                     entity_slug: str,
                     paid_date: date = None,
                     commit: bool = False):

        self.paid = True
        self.progress = Decimal.from_float(1.0)
        self.amount_paid = self.amount_due
        paid_dt = localdate() if not paid_date else paid_date

        if not self.paid_date:
            self.paid_date = paid_dt
        if self.paid_date > paid_dt:
            raise ValidationError(f'Cannot pay {self.__class__.__name__} in the future.')
        if self.paid_date < self.date:
            raise ValidationError(f'Cannot pay {self.__class__.__name__} before {self.__class__.__name__}'
                                  f' date {self.date}.')
        self.update_state()
        self.clean()
        if commit:
            self.migrate_state(
                user_model=user_model,
                entity_slug=entity_slug
            )
            self.save()
            ledger_model = self.ledger
            ledger_model.locked = True
            # pylint: disable=no-member
            ledger_model.save(update_fields=['locked', 'updated'])

    def migrate_state(self,
                      user_model,
                      entity_slug: str,
                      itemthrough_queryset: QuerySet = None,
                      force_migrate: bool = False,
                      commit: bool = True,
                      void: bool = False,
                      je_date: date = None):

        if not self.migrate_allowed() and not force_migrate:
            raise ValidationError(f'{self.REL_NAME_PREFIX.upper()} state migration not allowed')

        # getting current ledger state
        # pylint: disable=no-member
        txs_qs, txs_digest = self.ledger.digest(
            user_model=user_model,
            process_groups=True,
            process_roles=False,
            process_ratios=False,
            signs=False,
            by_unit=True
        )

        digest_data = txs_digest['tx_digest']['accounts']

        # Index (account_uuid, unit_uuid, balance_type, role)
        current_ledger_state = {
            (a['account_uuid'], a['unit_uuid'], a['balance_type']): a['balance'] for a in digest_data
            # (a['account_uuid'], a['unit_uuid'], a['balance_type'], a['role']): a['balance'] for a in digest_data
        }

        item_data = list(self.get_item_data(entity_slug=entity_slug, queryset=itemthrough_queryset))
        cogs_adjustment = defaultdict(lambda: Decimal('0.00'))
        inventory_adjustment = defaultdict(lambda: Decimal('0.00'))
        progress = self.get_progress()

        if isinstance(self, lazy_loader.get_bill_model()):

            for item in item_data:
                account_uuid_expense = item.get('item_model__expense_account__uuid')
                account_uuid_inventory = item.get('item_model__inventory_account__uuid')
                if account_uuid_expense:
                    item['account_uuid'] = account_uuid_expense
                    item['account_balance_type'] = item.get('item_model__expense_account__balance_type')
                elif account_uuid_inventory:
                    item['account_uuid'] = account_uuid_inventory
                    item['account_balance_type'] = item.get('item_model__inventory_account__balance_type')

        elif isinstance(self, lazy_loader.get_invoice_model()):

            for item in item_data:

                account_uuid_earnings = item.get('item_model__earnings_account__uuid')
                account_uuid_cogs = item.get('item_model__cogs_account__uuid')
                account_uuid_inventory = item.get('item_model__inventory_account__uuid')

                if account_uuid_earnings:
                    item['account_uuid'] = account_uuid_earnings
                    item['account_balance_type'] = item.get('item_model__earnings_account__balance_type')

                if account_uuid_cogs and account_uuid_inventory:

                    try:
                        irq = item.get('item_model__inventory_received')
                        irv = item.get('item_model__inventory_received_value')
                        tot_amt = 0
                        if irq is not None and irv is not None and irq != 0:
                            qty = item.get('quantity', Decimal('0.00'))
                            if not isinstance(qty, Decimal):
                                qty = Decimal.from_float(qty)
                            cogs_unit_cost = irv / irq
                            tot_amt = round(cogs_unit_cost * qty, 2)
                    except ZeroDivisionError:
                        tot_amt = 0

                    if tot_amt != 0:
                        # keeps track of necessary transactions to increase COGS account...
                        cogs_adjustment[(
                            account_uuid_cogs,
                            item.get('entity_unit__uuid'),
                            item.get('item_model__cogs_account__balance_type')
                        )] += tot_amt * progress

                        # keeps track of necessary transactions to reduce inventory account...
                        inventory_adjustment[(
                            account_uuid_inventory,
                            item.get('entity_unit__uuid'),
                            item.get('item_model__inventory_account__balance_type')
                        )] -= tot_amt * progress

        item_data_gb = groupby(item_data,
                               key=lambda a: (a['account_uuid'],
                                              a['entity_unit__uuid'],
                                              a['account_balance_type']))

        # scaling down item amount based on progress...
        progress_item_idx = {
            idx: round(sum(a['account_unit_total'] for a in ad) * progress, 2) for idx, ad in item_data_gb
        }

        # tuple ( unit_uuid, total_amount ) sorted by uuid...
        # sorting before group by...
        ua_gen = list((k[1], v) for k, v in progress_item_idx.items())
        ua_gen.sort(key=lambda a: str(a[0]) if a[0] else '')

        unit_amounts = {
            u: sum(a[1] for a in l) for u, l in groupby(ua_gen, key=lambda x: x[0])
        }
        total_amount = sum(unit_amounts.values())

        # { unit_uuid: float (percent) }
        unit_percents = {
            k: (v / total_amount) if progress and total_amount else Decimal('0.00') for k, v in unit_amounts.items()
        }

        if not void:
            new_state = self.new_state(commit=commit)
        else:
            new_state = self.void_state(commit=commit)

        amount_paid_split = self.split_amount(
            amount=new_state['amount_paid'],
            unit_split=unit_percents,
            account_uuid=self.cash_account_id,
            account_balance_type='debit'
        )
        amount_prepaid_split = self.split_amount(
            amount=new_state['amount_receivable'],
            unit_split=unit_percents,
            account_uuid=self.prepaid_account_id,
            account_balance_type='debit'
        )
        amount_unearned_split = self.split_amount(
            amount=new_state['amount_unearned'],
            unit_split=unit_percents,
            account_uuid=self.unearned_account_id,
            account_balance_type='credit'
        )

        new_ledger_state = dict()
        new_ledger_state.update(amount_paid_split)
        new_ledger_state.update(amount_prepaid_split)
        new_ledger_state.update(amount_unearned_split)

        if inventory_adjustment and cogs_adjustment:
            new_ledger_state.update(cogs_adjustment)
            new_ledger_state.update(inventory_adjustment)

        new_ledger_state.update(progress_item_idx)

        # list of all keys involved
        idx_keys = set(list(current_ledger_state) + list(new_ledger_state))

        # difference between new vs current
        diff_idx = {
            k: new_ledger_state.get(k, Decimal('0.00')) - current_ledger_state.get(k, Decimal('0.00')) for k in
            idx_keys if new_ledger_state.get(k, Decimal('0.00')) != Decimal('0.00')
        }

        if commit:
            JournalEntryModel = lazy_loader.get_journal_entry_model()
            TransactionModel = lazy_loader.get_transaction_model()

            unit_uuids = list(set(k[1] for k in idx_keys))
            now_date = localdate() if not je_date else je_date
            je_list = {
                u: JournalEntryModel.on_coa.create(
                    entity_unit_id=u,
                    date=now_date,
                    description=self.get_migrate_state_desc(),
                    activity='op',
                    origin='migration',
                    locked=True,
                    posted=True,
                    ledger_id=self.ledger_id
                ) for u in unit_uuids
            }

            txs_list = [
                (unit_uuid, TransactionModel(
                    journal_entry=je_list.get(unit_uuid),
                    amount=abs(round(amt, 2)),
                    tx_type=self.get_tx_type(acc_bal_type=bal_type, adjustment_amount=amt),
                    account_id=acc_uuid,
                    description=self.get_migrate_state_desc()
                )) for (acc_uuid, unit_uuid, bal_type), amt in diff_idx.items() if amt
            ]

            for unit_uuid, tx in txs_list:
                tx.clean()

            for uid in unit_uuids:
                # validates each unit txs independently...
                balance_tx_data(tx_data=[tx for ui, tx in txs_list if uid == ui], perform_correction=True)

            # validates all txs as a whole (for safety)...
            txs = [tx for ui, tx in txs_list]
            balance_tx_data(tx_data=txs, perform_correction=True)
            TransactionModel.objects.bulk_create(txs)
        return item_data, digest_data

    def void_state(self, commit: bool = False):
        void_state = {
            'amount_paid': 0,
            'amount_receivable': 0,
            'amount_unearned': 0,
            'amount_earned': 0
        }
        if commit:
            self.update_state(void_state)
        return void_state

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
            return self.TERMS_ON_RECEIPT
        elif due_in <= 30:
            return self.TERMS_NET_30
        elif due_in <= 60:
            return self.TERMS_NET_60
        elif due_in <= 90:
            return self.TERMS_NET_90
        return self.TERMS_NET_90_PLUS

    def clean(self):

        if not self.amount_due:
            self.amount_due = 0

        if not self.date:
            self.date = localdate()

        if self.cash_account_id is None:
            raise ValidationError('Must provide a cash account.')

        if self.accrue:
            if not self.prepaid_account_id:
                raise ValidationError(f'Accrued {self.__class__.__name__} must define a Prepaid Expense account.')
            if not self.unearned_account_id:
                raise ValidationError(f'Accrued {self.__class__.__name__} must define an Unearned Income account.')

        if any([
            self.cash_account_id is not None,
            self.prepaid_account_id is not None,
            self.unearned_account_id is not None
        ]):
            if not all([
                self.cash_account_id is not None,
                self.prepaid_account_id is not None,
                self.unearned_account_id is not None
            ]):
                raise ValidationError('Must provide all accounts Cash, Prepaid, UnEarned.')
            # pylint: disable=no-member
            if self.cash_account.role != ASSET_CA_CASH:
                raise ValidationError(f'Cash account must be of role {ASSET_CA_CASH}.')
            # pylint: disable=no-member
            if self.prepaid_account.role != ASSET_CA_PREPAID:
                raise ValidationError(f'Prepaid account must be of role {ASSET_CA_PREPAID}.')
            # pylint: disable=no-member
            if self.unearned_account.role != LIABILITY_CL_DEFERRED_REVENUE:
                raise ValidationError(f'Unearned account must be of role {LIABILITY_CL_DEFERRED_REVENUE}.')

        if self.accrue and self.progress is None:
            self.progress = 0

        if self.terms != self.TERMS_ON_RECEIPT:
            # pylint: disable=no-member
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
                raise ValidationError(f'Cannot pay {self.__class__.__name__} in the future.')
            if self.paid_date < self.date:
                raise ValidationError(f'Cannot pay {self.__class__.__name__} before {self.__class__.__name__}'
                                      f' date {self.date}.')
        else:
            self.paid_date = None

        if self.void and not all([
            self.amount_paid == 0,
            self.amount_earned == 0,
            self.amount_unearned == 0,
            self.amount_due == 0
        ]):
            raise ValidationError('Voided element cannot have any balance.')

        if self.migrate_allowed():
            self.update_state()


class MarkdownNotesMixIn(models.Model):
    markdown_notes = models.TextField(blank=True, null=True, verbose_name=_('Markdown Notes'))

    class Meta:
        abstract = True

    def notes_html(self):
        if not self.markdown_notes:
            return ''
        return markdown(force_str(self.markdown_notes))


class NodeTreeMixIn(models.Model):
    parent = models.ForeignKey('self',
                               null=True,
                               blank=True,
                               on_delete=models.CASCADE,
                               related_name='children_set')

    class Meta:
        abstract = True
