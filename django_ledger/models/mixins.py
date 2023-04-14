"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

This module implements the different model MixIns used on different Django Ledger Models to implement common
functionality.
"""
import logging
from collections import defaultdict
from datetime import timedelta, date, datetime
from decimal import Decimal
from itertools import groupby
from typing import Optional, Union, Dict
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from django.core.validators import int_list_validator
from django.db import models
from django.db.models import QuerySet
from django.utils.encoding import force_str
from django.utils.timezone import localdate, localtime
from django.utils.translation import gettext_lazy as _
from markdown import markdown

from django_ledger.io import (balance_tx_data, ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_DEFERRED_REVENUE,
                              validate_io_date)
from django_ledger.models.utils import lazy_loader

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


class SlugNameMixIn(models.Model):
    """
    Implements a slug field and a name field to a base Django Model.

    Attributes
    ----------
    slug: str
        A unique slug field to use as an index. Validates that the slug is at least 10 characters long.
    name: str
        A human-readable name for display purposes. Maximum 150 characters.
    """
    slug = models.SlugField(max_length=50,
                            editable=False,
                            unique=True,
                            validators=[
                                MinLengthValidator(limit_value=10,
                                                   message=_('Slug field must contain at least 10 characters.'))
                            ])
    name = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        abstract = True


class CreateUpdateMixIn(models.Model):
    """
    Implements a created and an updated field to a base Django Model.

    Attributes
    ----------
    created: datetime
        A created timestamp. Defaults to now().
    updated: str
        An updated timestamp used to identify when models are updated.
    """
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class ContactInfoMixIn(models.Model):
    """
    Implements a common set of fields used to document contact information.

    Attributes
    ----------
    address_1: str
        A string used to document the first line of an address. Mandatory. Max length is 70.
    address_2: str
        A string used to document the first line of an address. Optional.
    city: str
        A string used to document the city. Optional.
    state: str
        A string used to document the State of Province. Optional.
    zip_code: str
        A string used to document the ZIP code. Optional
    country: str
       A string used to document the country. Optional.
    email: str
        A string used to document the contact email. Uses django's EmailField for validation.
    website: str
        A string used to document the contact website. Uses django's URLField for validation.
    phone: str
        A string used to document the contact phone.
    """
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


class AccrualMixIn(models.Model):
    """
    Implements functionality used to track accruable financial instruments to a base Django Model.
    Examples of this include bills and invoices expenses/income, that depending on the Entity's accrual method, may
    be recognized on the Income Statement differently.

    Attributes
    ----------
    amount_due: Decimal
        The total amount due of the financial instrument.
    amount_paid: Decimal
        The total amount paid or settled.
    amount_receivable: Decimal
        The total amount allocated to Accounts Receivable based on the progress.
    amount_unearned: Decimal
        The total amount allocated to Accounts Payable based on the progress.
    amount_earned:
        The total amount that is recognized on the earnings based on progress.
    accrue: bool
        If True, the financial instrument will follow the Accrual Method of Accounting, otherwise it will follow the
        Cash Method of Accounting. Defaults to the EntityModel preferred method of accounting.
    progress: Decimal
        A decimal number representing the amount of progress of the financial instrument. Value is between 0.00 and 1.00.
    ledger: LedgerModel
        The LedgerModel associated with the Accruable financial instrument.
    cash_account: AccountModel
        The AccountModel used to track cash payments to the financial instrument. Must be of role ASSET_CA_CASH.
    prepaid_account: AccountModel
        The AccountModel used to track receivables to the financial instrument. Must be of role ASSET_CA_PREPAID.
    unearned_account: AccountModel
        The AccountModel used to track receivables to the financial instrument. Must be of role
        LIABILITY_CL_DEFERRED_REVENUE.
    """
    IS_DEBIT_BALANCE = None
    REL_NAME_PREFIX = None
    ALLOW_MIGRATE = True
    TX_TYPE_MAPPING = {
        'ci': 'credit',
        'dd': 'credit',
        'cd': 'debit',
        'di': 'debit',
    }

    amount_due = models.DecimalField(default=0,
                                     max_digits=20,
                                     decimal_places=2,
                                     verbose_name=_('Amount Due'))

    amount_paid = models.DecimalField(default=0,
                                      max_digits=20,
                                      decimal_places=2,
                                      verbose_name=_('Amount Paid'),
                                      validators=[MinValueValidator(limit_value=0)])

    amount_receivable = models.DecimalField(default=0,
                                            max_digits=20,
                                            decimal_places=2,
                                            verbose_name=_('Amount Receivable'),
                                            validators=[MinValueValidator(limit_value=0)])
    amount_unearned = models.DecimalField(default=0,
                                          max_digits=20,
                                          decimal_places=2,
                                          verbose_name=_('Amount Unearned'),
                                          validators=[MinValueValidator(limit_value=0)])
    amount_earned = models.DecimalField(default=0,
                                        max_digits=20,
                                        decimal_places=2,
                                        verbose_name=_('Amount Earned'),
                                        validators=[MinValueValidator(limit_value=0)])

    accrue = models.BooleanField(default=False, verbose_name=_('Accrue'))

    # todo: change progress method from percent to currency amount and FloatField??...
    progress = models.DecimalField(default=0,
                                   verbose_name=_('Progress Amount'),
                                   decimal_places=2,
                                   max_digits=3,
                                   validators=[
                                       MinValueValidator(limit_value=0),
                                       MaxValueValidator(limit_value=1)
                                   ])

    # todo: rename to ledger_model...
    ledger = models.OneToOneField('django_ledger.LedgerModel',
                                  editable=False,
                                  verbose_name=_('Ledger'),
                                  on_delete=models.CASCADE)
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.RESTRICT,
                                     blank=True,
                                     null=True,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    prepaid_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.RESTRICT,
                                        blank=True,
                                        null=True,
                                        verbose_name=_('Prepaid Account'),
                                        related_name=f'{REL_NAME_PREFIX}_prepaid_account')
    unearned_account = models.ForeignKey('django_ledger.AccountModel',
                                         on_delete=models.RESTRICT,
                                         blank=True,
                                         null=True,
                                         verbose_name=_('Unearned Account'),
                                         related_name=f'{REL_NAME_PREFIX}_unearned_account')

    class Meta:
        abstract = True

    # STATES..
    def is_configured(self) -> bool:
        """
        Determines if the accruable financial instrument is properly configured.

        Returns
        -------
        bool
            True if configured, else False.
        """
        return all([
            self.ledger_id is not None,
            self.cash_account_id is not None,
            self.unearned_account_id is not None,
            self.prepaid_account_id is not None
        ])

    def is_posted(self):
        """
        Determines if the accruable financial instrument is posted.
        Results in additional Database query if 'ledger' field is not pre-fetch on QuerySet.

        Returns
        -------
        bool
            True if posted, else False.
        """
        return self.ledger.posted

    # OTHERS...
    def get_progress(self) -> Union[Decimal, float]:
        """
        Determines the progress amount based on amount due, amount paid and accrue field.

        Returns
        -------
        Decimal
            Financial instrument progress as a Decimal.
        """
        if self.accrue:
            return self.progress
        if not self.amount_due:
            return Decimal.from_float(0.00)
        return (self.amount_paid or Decimal.from_float(0.00)) / self.amount_due

    def get_progress_percent(self) -> float:
        """
        Determines the progress amount as percent based on amount due, amount paid and accrue field.

        Returns
        -------
        float
            Financial instrument progress as a percent.
        """
        return round(self.get_progress() * 100, 2)

    def get_amount_cash(self) -> Union[Decimal, float]:
        """
        Determines the impact to the EntityModel cash balance based on the financial instrument debit or credit
        configuration. i.e, Invoices are debit financial instrument because payments to invoices increase cash.

        Returns
        -------
        float
            Financial instrument progress as a percent.
        """
        if self.IS_DEBIT_BALANCE:
            return self.amount_paid
        elif not self.IS_DEBIT_BALANCE:
            return -self.amount_paid

    def get_amount_earned(self) -> Union[Decimal, float]:
        """
        Determines the impact to the EntityModel earnings based on financial instrument progress.

        Returns
        -------
        float or Decimal
            Financial instrument amount earned.
        """
        if self.accrue:
            amount_due = self.amount_due or Decimal.from_float(0.00)
            return self.get_progress() * amount_due
        else:
            return self.amount_paid or Decimal.from_float(0.00)

    def get_amount_prepaid(self) -> Union[Decimal, float]:
        """
        Determines the impact to the EntityModel Accounts Receivable based on financial instrument progress.

        Returns
        -------
        float or Decimal
            Financial instrument amount prepaid.
        """
        payments = self.amount_paid or Decimal.from_float(0.00)
        if self.accrue:
            amt_earned = self.get_amount_earned()
            if all([
                self.IS_DEBIT_BALANCE,
                amt_earned >= payments
            ]):
                return self.get_amount_earned() - payments
            elif all([
                not self.IS_DEBIT_BALANCE,
                amt_earned <= payments
            ]):
                return payments - self.get_amount_earned()
        return Decimal.from_float(0.00)

    def get_amount_unearned(self) -> Union[Decimal, float]:
        """
        Determines the impact to the EntityModel Accounts Payable based on financial instrument progress.

        Returns
        -------
        float or Decimal
            Financial instrument amount unearned.
        """
        if self.accrue:
            amt_earned = self.get_amount_earned()
            if all([
                self.IS_DEBIT_BALANCE,
                amt_earned <= self.amount_paid
            ]):
                return self.amount_paid - amt_earned
            elif all([
                not self.IS_DEBIT_BALANCE,
                amt_earned >= self.amount_paid
            ]):
                return amt_earned - self.amount_paid
        return Decimal.from_float(0.00)

    def get_amount_open(self) -> Union[Decimal, float]:
        """
        Determines the open amount left to be progressed.

        Returns
        -------
        float or Decimal
            Financial instrument amount open.
        """
        if self.accrue:
            amount_due = self.amount_due or 0.00
            return amount_due - self.get_amount_earned()
        amount_due = self.amount_due or 0.00
        payments = self.amount_paid or 0.00
        return amount_due - payments

    def get_migration_data(self, queryset: QuerySet = None):
        raise NotImplementedError('Must implement get_migration_data method.')

    def get_migrate_state_desc(self, *args, **kwargs):
        raise NotImplementedError('Must implement get_migrate_state_desc method.')

    def can_migrate(self) -> bool:
        """
        Determines if the Accruable financial instrument can be migrated to the books.
        Results in additional Database query if 'ledger' field is not pre-fetch on QuerySet.

        Returns
        -------
        bool
            True if can migrate, else False.
        """
        if not self.ledger_id:
            return False
        return not self.ledger.locked

    def get_tx_type(self,
                    acc_bal_type: dict,
                    adjustment_amount: Decimal):
        """
        Determines the transaction type associated with an increase/decrease of an account balance of the financial
        instrument.

        Parameters
        ----------
        acc_bal_type:
            The balance type of the account to be adjusted.
        adjustment_amount: Decimal
            The adjustment, whether positive or negative.

        Returns
        -------
        str
            The transaction type of the account adjustment.
        """
        acc_bal_type = acc_bal_type[0]
        d_or_i = 'd' if adjustment_amount < 0.00 else 'i'
        return self.TX_TYPE_MAPPING[acc_bal_type + d_or_i]

    @classmethod
    def split_amount(cls, amount: Union[Decimal, float],
                     unit_split: Dict,
                     account_uuid: UUID,
                     account_balance_type: str) -> Dict:
        """
        Splits an amount into different proportions representing the unit splits.
        Makes sure that 100% of the amount is numerically allocated taking into consideration decimal points.

        Parameters
        ----------
        amount: Decimal or float
            The amount to be split.
        unit_split: dict
            A dictionary with information related to each unit split and proportions.
        account_uuid: UUID
            The AccountModel UUID associated with the splits.
        account_balance_type: str
            The AccountModel balance type to determine whether to perform a credit or a debit.

        Returns
        -------
        dict
            A dictionary with the split information.
        """
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

    # LOCK/UNLOCK Ledger...
    def lock_ledger(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        """
        Convenience method to lock the LedgerModel associated with the Accruable financial instrument.

        Parameters
        ----------
        commit: bool
            Commits the transaction in the database. Defaults to False.
        raise_exception: bool
            If True, raises ValidationError if LedgerModel already locked.
        """
        ledger_model = self.ledger
        if ledger_model.locked:
            if raise_exception:
                raise ValidationError(f'Bill ledger {ledger_model.name} is already locked...')
        ledger_model.lock(commit)

    def unlock_ledger(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        """
        Convenience method to un-lock the LedgerModel associated with the Accruable financial instrument.

        Parameters
        ----------
        commit: bool
            Commits the transaction in the database. Defaults to False.
        raise_exception: bool
            If True, raises ValidationError if LedgerModel already locked.
        """
        ledger_model = self.ledger
        if not ledger_model.locked:
            if raise_exception:
                raise ValidationError(f'Bill ledger {ledger_model.name} is already unlocked...')
        ledger_model.unlock(commit)

    # POST/UNPOST Ledger...
    def post_ledger(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        """
        Convenience method to post the LedgerModel associated with the Accruable financial instrument.

        Parameters
        ----------
        commit: bool
            Commits the transaction in the database. Defaults to False.
        raise_exception: bool
            If True, raises ValidationError if LedgerModel already locked.
        """
        ledger_model = self.ledger
        if ledger_model.posted:
            if raise_exception:
                raise ValidationError(f'Bill ledger {ledger_model.name} is already posted...')
        ledger_model.post(commit)

    def unpost_ledger(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        """
        Convenience method to un-lock the LedgerModel associated with the Accruable financial instrument.

        Parameters
        ----------
        commit: bool
            Commits the transaction in the database. Defaults to False.
        raise_exception: bool
            If True, raises ValidationError if LedgerModel already locked.
        """
        ledger_model = self.ledger
        if not ledger_model.posted:
            if raise_exception:
                raise ValidationError(f'Bill ledger {ledger_model.name} is not posted...')
        ledger_model.post(commit)

    def migrate_state(self,
                      user_model,
                      entity_slug: str,
                      itemtxs_qs: Optional[QuerySet] = None,
                      force_migrate: bool = False,
                      commit: bool = True,
                      void: bool = False,
                      je_date: Optional[Union[str, date, datetime]] = None,
                      raise_exception: bool = True,
                      **kwargs):

        """
        Migrates the current Accruable financial instrument into the books. The main objective of the migrate_state
        method is to determine the JournalEntry and TransactionModels necessary to accurately reflect the financial
        instrument state in the books.

        Parameters
        ----------
        user_model
            The Django User Model.
        entity_slug: str
            The EntityModel slug.
        itemtxs_qs: ItemTransactionModelQuerySet
            The pre-fetched ItemTransactionModelQuerySet containing the item information associated with the financial
            element migration. If provided, will avoid additional database query.
        force_migrate: bool
            Forces migration of the financial instrument bypassing the can_migrate() check.
        commit: bool
            If True the migration will be committed in the database. Defaults to True.
        void: bool
            If True, the migration will perform a VOID actions of the financial instrument.
        je_date: date
            The JournalEntryModel date to be used for this migration.
        raise_exception: bool
            Raises ValidationError if migration is not allowed. Defaults to True.

        Returns
        -------
        tuple
            A tuple of the ItemTransactionModel and the Digest Result from IOMixIn.
        """

        if self.can_migrate() or force_migrate:

            # getting current ledger state
            txs_qs, txs_digest = self.ledger.digest(
                user_model=user_model,
                entity_slug=entity_slug,
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

            item_data = list(self.get_migration_data(queryset=itemtxs_qs))
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
                idx_keys
            }

            # eliminates transactions with no amount...
            diff_idx = {
                k: v for k, v in diff_idx.items() if v
            }

            if commit:
                JournalEntryModel = lazy_loader.get_journal_entry_model()
                TransactionModel = lazy_loader.get_transaction_model()

                unit_uuids = list(set(k[1] for k in idx_keys))

                if je_date:
                    je_date = validate_io_date(dt=je_date)

                now_timestamp = localtime() if not je_date else je_date
                je_list = {
                    u: JournalEntryModel(
                        entity_unit_id=u,
                        timestamp=now_timestamp,
                        description=self.get_migrate_state_desc(),
                        origin='migration',
                        ledger_id=self.ledger_id
                    ) for u in unit_uuids
                }

                for u, je in je_list.items():
                    je.clean(verify=False)

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

                for _, je in je_list.items():
                    # will independently verify and populate appropriate activity for JE.
                    je.clean(verify=True)
                    if je.is_verified():
                        je.mark_as_posted(commit=False, verify=False, raise_exception=True)
                        je.mark_as_locked(commit=False, raise_exception=True)

                if all([je.is_verified() for _, je in je_list.items()]):
                    # only if all JEs have been verified will be posted and locked...
                    JournalEntryModel.objects.bulk_update(
                        objs=[je for _, je in je_list.items()],
                        fields=['posted', 'locked', 'activity']
                    )

            return item_data, txs_digest
        else:
            if raise_exception:
                raise ValidationError(f'{self.REL_NAME_PREFIX.upper()} state migration not allowed')

    def void_state(self, commit: bool = False) -> Dict:
        """
        Determines the VOID state of the financial instrument.

        Parameters
        ----------
        commit: bool
            Commits the new financial instrument state into the model.

        Returns
        -------
        dict
            A dictionary with new amount_paid, amount_receivable, amount_unearned and amount_earned as keys.
        """
        void_state = {
            'amount_paid': Decimal.from_float(0.00),
            'amount_receivable': Decimal.from_float(0.00),
            'amount_unearned': Decimal.from_float(0.00),
            'amount_earned': Decimal.from_float(0.00),
        }
        if commit:
            self.update_state(void_state)
        return void_state

    def new_state(self, commit: bool = False):
        """
        Determines the new state of the financial instrument based on progress.

        Parameters
        ----------
        commit: bool
            Commits the new financial instrument state into the model.

        Returns
        -------
        dict
            A dictionary with new amount_paid, amount_receivable, amount_unearned and amount_earned as keys.
        """
        new_state = {
            'amount_paid': self.get_amount_cash(),
            'amount_receivable': self.get_amount_prepaid(),
            'amount_unearned': self.get_amount_unearned(),
            'amount_earned': self.get_amount_earned()
        }
        if commit:
            self.update_state(new_state)
        return new_state

    def update_state(self, state: Optional[Dict] = None):
        """
        Updates the state on the financial instrument.

        Parameters
        ----------
        state: dict
            Optional user provided state to use.
        """
        if not state:
            state = self.new_state()
        self.amount_paid = abs(state['amount_paid'])
        self.amount_receivable = state['amount_receivable']
        self.amount_unearned = state['amount_unearned']
        self.amount_earned = state['amount_earned']

    def clean(self):

        if not self.amount_due:
            self.amount_due = 0

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
            self.progress = Decimal.from_float(0.00)

        if self.amount_paid > self.amount_due:
            raise ValidationError(f'Amount paid {self.amount_paid} cannot exceed amount due {self.amount_due}')

        if self.is_paid():
            self.progress = Decimal.from_float(1.0)
            self.amount_paid = self.amount_due
            today = localdate()

            if not self.date_paid:
                self.date_paid = today
            if self.date_paid > today:
                raise ValidationError(f'Cannot pay {self.__class__.__name__} in the future.')
        else:
            self.date_paid = None

        if self.is_void():
            if any([
                self.amount_paid,
                self.amount_earned,
                self.amount_unearned,
                self.amount_receivable
            ]):
                raise ValidationError('Voided element cannot have any balance.')

            self.progress = Decimal.from_float(0.00)

        if self.can_migrate():
            self.update_state()


class PaymentTermsMixIn(models.Model):
    """
    Implements functionality used to track dates relate to various payment terms.
    Examples of this include tracking bills and invoices that are due on receipt, 30, 60 or 90 days after they are
    approved.

    Attributes
    ----------
    terms: str
        A choice of TERM_CHOICES that determines the payment terms.

    """
    TERMS_ON_RECEIPT = 'on_receipt'
    TERMS_NET_30 = 'net_30'
    TERMS_NET_60 = 'net_60'
    TERMS_NET_90 = 'net_90'
    TERMS_NET_90_PLUS = 'net_90+'

    TERM_CHOICES = [
        (TERMS_ON_RECEIPT, 'Due On Receipt'),
        (TERMS_NET_30, 'Net 30 Days'),
        (TERMS_NET_60, 'Net 60 Days'),
        (TERMS_NET_90, 'Net 90 Days'),
    ]

    TERM_DAYS_MAPPING = {
        TERMS_ON_RECEIPT: 0,
        TERMS_NET_30: 30,
        TERMS_NET_60: 60,
        TERMS_NET_90: 90,
        TERMS_NET_90_PLUS: 120
    }

    terms = models.CharField(max_length=10,
                             default='on_receipt',
                             choices=TERM_CHOICES,
                             verbose_name=_('Terms'))
    date_due = models.DateField(verbose_name=_('Due Date'), null=True, blank=True)

    class Meta:
        abstract = True

    def get_terms_start_date(self) -> date:
        """
        Determines the start date for the terms of payment.

        Returns
        -------
        date
            The date when terms of payment starts.
        """
        raise NotImplementedError(
            f'Must implement get_terms_start_date() for {self.__class__.__name__}'
        )

    def get_terms_net_90_plus(self) -> int:
        """
        Determines the number of days for 90+ days terms of payment.

        Returns
        -------
        date
            The date when terms of payment starts.
        """
        return 120

    def get_terms_timedelta_days(self) -> int:
        """
        Determines the number of days from the terms start date.

        Returns
        -------
        int
            The number of days as integer.
        """
        if self.terms == self.TERMS_NET_90_PLUS:
            return self.get_terms_net_90_plus()
        return self.TERM_DAYS_MAPPING[self.terms]

    def get_terms_timedelta(self) -> timedelta:
        """
        Calculates a timedelta relative to the terms start date.

        Returns
        -------
        timedelta
            Timedelta relative to terms start date.
        """
        return timedelta(days=self.get_terms_timedelta_days())

    def due_in_days(self) -> Optional[int]:
        """
        Determines how many days until the due date.

        Returns
        -------
        int
            Days as integer.
        """
        if self.date_due:
            td = self.date_due - localdate()
            if td.days < 0:
                return 0
            return td.days

    # todo: is this necessary?...
    def net_due_group(self):
        """
        Determines the group where the financial instrument falls based on the number of days until the due date.

        Returns
        -------
        str
            The terms group as a string.
        """
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
        terms_start_date = self.get_terms_start_date()
        if terms_start_date:
            if self.terms != self.TERMS_ON_RECEIPT:
                self.date_due = terms_start_date + self.get_terms_timedelta()
            else:
                self.date_due = terms_start_date


class MarkdownNotesMixIn(models.Model):
    """
    Implements functionality used to add a Mark-Down notes to a base Django Model.

    Attributes
    ----------
    markdown_notes: str
        A string of text representing the mark-down document.
    """
    markdown_notes = models.TextField(blank=True, null=True, verbose_name=_('Markdown Notes'))

    class Meta:
        abstract = True

    def notes_html(self):
        """
        Compiles the markdown_notes field into html.

        Returns
        -------
        str
            Compiled HTML document as a string.
        """
        if not self.markdown_notes:
            return ''
        return markdown(force_str(self.markdown_notes))


class BankAccountInfoMixIn(models.Model):
    """
    Implements functionality used to add bank account details to base Django Models.

    Attributes
    ----------
    account_number: str
        The Bank Account number. Only Digits are allowed. Max 30 digists.
    routing_number: str
        Routing number for the concerned bank account. Also called as 'Routing Transit Number (RTN)'. Max 30 digists.
    aba_number: str
        The American Bankers Association Number assigned to each bank.
    account_type: str
        A choice of ACCOUNT_TYPES. Each account will have to select from the available choices Checking, Savings.
    swift_number: str
        SWIFT electronic communications network number of the bank institution.
    """

    ACCOUNT_CHECKING = 'checking'
    ACCOUNT_SAVINGS = 'savings'
    ACCOUNT_TYPES = [
        (ACCOUNT_CHECKING, _('Checking')),
        (ACCOUNT_SAVINGS, _('Savings'))
    ]

    account_number = models.CharField(max_length=30, null=True, blank=True,
                                      validators=[
                                          int_list_validator(sep='', message=_('Only digits allowed'))
                                      ], verbose_name=_('Account Number'))
    routing_number = models.CharField(max_length=30, null=True, blank=True,
                                      validators=[
                                          int_list_validator(sep='', message=_('Only digits allowed'))
                                      ], verbose_name=_('Routing Number'))
    aba_number = models.CharField(max_length=30, null=True, blank=True, verbose_name=_('ABA Number'))
    swift_number = models.CharField(max_length=30, null=True, blank=True, verbose_name=_('SWIFT Number'))
    account_type = models.CharField(choices=ACCOUNT_TYPES,
                                    max_length=10,
                                    default=ACCOUNT_CHECKING,
                                    verbose_name=_('Account Type'))

    class Meta:
        abstract = True


class TaxInfoMixIn(models.Model):
    tax_id_number = models.CharField(max_length=30,
                                     null=True,
                                     blank=True,
                                     verbose_name=_('Tax Registration Number'))

    class Meta:
        abstract = True


class TaxCollectionMixIn(models.Model):
    """
    Implements functionality used to add tax collection rates and or withholding to a base Django Model.
    This field may be used to set a pre-defined withholding rate to a financial instrument, customer, vendor, etc.

    Attributes
    ----------
    sales_tax_rate: float
        The tax rate as a float. A Number between 0.00 and 1.00.
    """
    sales_tax_rate = models.FloatField(default=0.00000,
                                       verbose_name=_('Sales Tax Rate'),
                                       null=True,
                                       blank=True,
                                       validators=[
                                           MinValueValidator(limit_value=0.00000),
                                           MaxValueValidator(limit_value=1.00000)
                                       ])

    class Meta:
        abstract = True


class LoggingMixIn:
    """
    Implements functionality used to add logging capabilities to any python class.
    Useful for production and or testing environments.
    """
    LOGGER_NAME_ATTRIBUTE = None
    LOGGER_BYPASS_DEBUG = False

    def get_logger_name(self):
        if self.LOGGER_NAME_ATTRIBUTE is None:
            raise NotImplementedError(f'{self.__class__.__name__} must define LOGGER_NAME_ATTRIBUTE of implement '
                                      'get_logger_name() function.')
        return getattr(self, self.LOGGER_NAME_ATTRIBUTE)

    def get_logger(self) -> logging.Logger:
        name = self.get_logger_name()
        return logging.getLogger(name)

    def send_log(self, msg, level, force):
        if self.LOGGER_BYPASS_DEBUG or settings.DEBUG or force:
            logger = self.get_logger()
            logger.log(msg=msg, level=level)
