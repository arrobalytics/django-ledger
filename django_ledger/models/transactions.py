"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import datetime
from typing import List
from uuid import uuid4, UUID

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.accounts import AccountModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.unit import EntityUnitModel


"""
One of the major model which is used for storing the Transactions recorded in the entity model
Every transaction which has an financial implication must be recorded in the books

For each transaction, the debits and credits should be matched. Ay transaction will be reflecting in the Financial statements only after the same has been posted


"""

class TransactionQuerySet(models.QuerySet):

    """
    A custom defined Query Set for the TransactionModel.
    This implements multiple methods or queries that we need to run to get a list of all the transactions.
    """
    def posted(self):
        """ Used to select the transaction which are in 'posted' state """
        return self.filter(
            Q(journal_entry__posted=True) &
            Q(journal_entry__ledger__posted=True)
        )

    def for_user(self, user_model):
        """this will authenticate the user and allow the users only to view the transaction for which he is authorized """
        return self.filter(
            Q(journal_entry__ledger__entity__admin=user_model) |
            Q(journal_entry__ledger__entity__managers__in=[user_model])
        )

    def for_accounts(self, account_list: List[str or AccountModel]):
        """This helps to view the transactions for a particular account. We can pass in one particular account of a list of accounts"""
        if len(account_list) > 0 and isinstance(account_list[0], str):
            return self.filter(account__code__in=account_list)
        return self.filter(account__in=account_list)

    def for_roles(self, role_list: List[str]):
        return self.filter(account__role__in=role_list)

    def for_unit(self, unit_slug: str):
        return self.filter(journal_entry__ledger__unit__slug__exact=unit_slug)

    def for_activity(self, activity_list: List[str]):
        return self.filter(journal_entry__activity__in=activity_list)

    def to_date(self, to_date: str or datetime):
        return self.filter(journal_entry__date__lte=to_date)

    def from_date(self, from_date: str or datetime):
        return self.filter(journal_entry__date__gte=from_date)


class TransactionModelAdmin(models.Manager):

    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db)

    def for_user(self, user_model):
        return self.filter(
            Q(journal_entry__ledger__entity__admin=user_model) |
            Q(journal_entry__ledger__entity__managers__in=[user_model])
        )

    def for_entity(self,
                   user_model,
                   entity_slug: str = None):
        qs = self.for_user(user_model=user_model)
        if isinstance(entity_slug, EntityModel):
            return qs.filter(journal_entry__ledger__entity=entity_slug)
        elif isinstance(entity_slug, str):
            return qs.filter(journal_entry__ledger__entity__slug__exact=entity_slug)

    def for_ledger(self,
                   user_model,
                   ledger_model: LedgerModel = None):
        qs = self.for_user(user_model=user_model)
        if isinstance(ledger_model, LedgerModel):
            return qs.filter(journal_entry__ledger=ledger_model)
        elif isinstance(ledger_model, str) or isinstance(ledger_model, UUID):
            return qs.filter(journal_entry__ledger__uuid__exact=ledger_model)

    def for_unit(self,
                 user_model,
                 entity_slug: str,
                 unit_model: EntityUnitModel = None,
                 unit_slug: str = None):

        if not unit_model and not unit_slug:
            raise ValueError(f'None unit_model or unit_slug were provided.')
        elif unit_model and unit_slug:
            raise ValueError(f'Must pass either unit_model or unit_slug, not both.')

        qs = self.for_entity(user_model=user_model, entity_slug=entity_slug)

        if unit_model and isinstance(unit_model, EntityUnitModel):
            return qs.filter(journal_entry__entity_unit=unit_model)
        elif unit_slug and isinstance(unit_slug, str):
            return qs.filter(journal_entry__entity_unit__slug__exact=unit_slug)

    def for_journal_entry(self,
                          user_model,
                          entity_slug: str,
                          ledger_pk: str,
                          je_pk: str):
        qs = self.get_queryset()
        return qs.filter(
            Q(journal_entry__ledger__entity__slug__exact=entity_slug) &
            Q(journal_entry__ledger__uuid__exact=ledger_pk) &
            Q(journal_entry__uuid__exact=je_pk) &
            (
                    Q(journal_entry__ledger__entity__admin=user_model) |
                    Q(journal_entry__ledger__entity__managers__in=[user_model])
            )
        )

    def for_account(self,
                    account_pk: str,
                    # coa_slug: str,
                    user_model,
                    entity_slug: str = None):
        qs = self.get_queryset()
        return qs.filter(
            Q(journal_entry__ledger__entity__slug__exact=entity_slug) &
            # Q(account__coa__slug__exact=coa_slug) &
            Q(account_id=account_pk) &
            (
                    Q(journal_entry__ledger__entity__admin=user_model) |
                    Q(journal_entry__ledger__entity__managers__in=[user_model])
            )
        )

    def for_bill(self,
                 bill_pk: str,
                 user_model,
                 entity_slug: str):
        qs = self.for_entity(
            user_model=user_model,
            entity_slug=entity_slug)
        return qs.filter(journal_entry__ledger__billmodel__uuid__exact=bill_pk)

    def for_invoice(self,
                    invoice_pk: str,
                    user_model,
                    entity_slug: str):
        qs = self.for_entity(
            user_model=user_model,
            entity_slug=entity_slug)
        return qs.filter(journal_entry__ledger__invoicemodel__uuid__exact=invoice_pk)


class TransactionModelAbstract(CreateUpdateMixIn):
    CREDIT = 'credit'
    DEBIT = 'debit'

    TX_TYPE = [
        (CREDIT, _('Credit')),
        (DEBIT, _('Debit'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    tx_type = models.CharField(max_length=10, choices=TX_TYPE, verbose_name=_('Tx Type'))
    journal_entry = models.ForeignKey('django_ledger.JournalEntryModel',
                                      editable=False,
                                      related_name='txs',
                                      verbose_name=_('Journal Entry'),
                                      help_text=_('Journal Entry to be associated with this transaction.'),
                                      on_delete=models.PROTECT)
    account = models.ForeignKey('django_ledger.AccountModel',
                                related_name='txs',
                                verbose_name=_('Account'),
                                help_text=_('Account from Chart of Accounts to be associated with this transaction.'),
                                on_delete=models.PROTECT)
    amount = models.DecimalField(decimal_places=2,
                                 max_digits=20,
                                 null=True,
                                 blank=True,
                                 verbose_name=_('Amount'),
                                 help_text=_('Account of the transaction.'),
                                 validators=[MinValueValidator(0)])
    description = models.CharField(max_length=100, null=True, blank=True,
                                   verbose_name=_('Tx Description'),
                                   help_text=_('A description to be included with this individual transaction'))
    objects = TransactionModelAdmin()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        indexes = [
            models.Index(fields=['tx_type']),
            models.Index(fields=['account']),
            models.Index(fields=['journal_entry']),
            models.Index(fields=['created']),
            models.Index(fields=['updated'])
        ]

    def __str__(self):
        # pylint: disable=no-member
        return '{x1}-{x2}/{x5}: {x3}/{x4}'.format(x1=self.account.code,
                                                  x2=self.account.name,
                                                  x3=self.amount,
                                                  x4=self.tx_type,
                                                  # pylint: disable=no-member
                                                  x5=self.account.balance_type)


class TransactionModel(TransactionModelAbstract):
    """
    Base Transaction Model From Abstract.
    This is a new documentation.
    """
