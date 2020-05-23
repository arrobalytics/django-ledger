from datetime import datetime
from typing import List

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from django_ledger.abstracts.mixins.base import CreateUpdateMixIn
from django_ledger.models.accounts import AccountModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journalentry import JournalEntryModel
from django_ledger.models.ledger import LedgerModel


class TransactionQuerySet(models.QuerySet):
    def posted(self):
        return self.filter(
            Q(journal_entry__posted=True) &
            Q(journal_entry__ledger__posted=True)
        )

    def for_ledger(self, ledger_model: LedgerModel):
        return self.filter(journal_entry__ledger=ledger_model)

    def for_journal_entry(self, journal_entry_model: JournalEntryModel):
        return self.filter(journal_entry=journal_entry_model)

    def for_entity(self, entity_slug: EntityModel or str):
        if isinstance(entity_slug, EntityModel):
            entity_slug = entity_slug.slug
        return self.filter(journal_entry__ledger__entity__slug__exact=entity_slug)

    def for_user(self, user_model):
        return self.filter(
            Q(journal_entry__ledger__entity__admin=user_model) |
            Q(journal_entry__ledger__entity__managers__exact=user_model)
        )

    def for_accounts(self, account_list: List[str or AccountModel]):
        if len(account_list) > 0 and isinstance(account_list[0], str):
            return self.filter(account__code__in=account_list)
        else:
            return self.filter(account__in=account_list)

    def for_roles(self, role_list: List[str]):
        return self.filter(account__role__in=role_list)

    def for_activity(self, activity_list: List[str]):
        return self.filter(journal_entry__activity__in=activity_list)

    def as_of(self, as_of_date: str or datetime):
        return self.filter(journal_entry__date__lte=as_of_date)


class TransactionModelAdmin(models.Manager):

    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db)

    def posted(self):
        qs = self.get_queryset()
        return qs.filter(
            Q(journal_entry__posted=True) &
            Q(journal_entry__ledger__posted=True)
        )

    def for_ledger(self, ledger_model: LedgerModel):
        qs = self.get_queryset()
        return qs.filter(journal_entry__ledger=ledger_model)

    def for_journal_entry(self, journal_entry_model: JournalEntryModel):
        qs = self.get_queryset()
        return qs.filter(journal_entry=journal_entry_model)

    def for_entity(self, entity_slug: EntityModel or str):
        if isinstance(entity_slug, EntityModel):
            entity_slug = entity_slug.slug
        qs = self.get_queryset()
        return qs.filter(journal_entry__ledger__entity__slug__exact=entity_slug)

    def for_user(self, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(journal_entry__ledger__entity__admin=user_model) |
            Q(journal_entry__ledger__entity__managers__exact=user_model)
        )

    def for_accounts(self, account_list: List[str or AccountModel]):
        qs = self.get_queryset()
        if len(account_list) > 0 and isinstance(account_list[0], str):
            return qs.filter(account__code__in=account_list)
        else:
            return qs.filter(account__in=account_list)

    def for_roles(self, role_list: List[str]):
        qs = self.get_queryset()
        return qs.filter(account__role__in=role_list)

    def for_activity(self, activity_list: List[str]):
        qs = self.get_queryset()
        return qs.filter(journal_entry__activity__in=activity_list)

    def as_of(self, as_of_date: str or datetime):
        qs = self.get_queryset()
        return qs.filter(journal_entry__date__lte=as_of_date)


class TransactionModelAbstract(CreateUpdateMixIn):
    CREDIT = 'credit'
    DEBIT = 'debit'

    TX_TYPE = [
        (CREDIT, _('Credit')),
        (DEBIT, _('Debit'))
    ]
    tx_type = models.CharField(max_length=10, choices=TX_TYPE, verbose_name=_l('Tx Type'))
    journal_entry = models.ForeignKey('django_ledger.JournalEntryModel',
                                      related_name='txs',
                                      verbose_name=_l('Journal Entry'),
                                      on_delete=models.CASCADE)
    account = models.ForeignKey('django_ledger.AccountModel',
                                related_name='txs',
                                verbose_name=_l('Account'),
                                on_delete=models.PROTECT)
    amount = models.DecimalField(decimal_places=2,
                                 max_digits=20,
                                 null=True,
                                 blank=True,
                                 verbose_name=_l('Amount'),
                                 validators=[MinValueValidator(0)])
    description = models.CharField(max_length=100, null=True, blank=True, verbose_name=_l('Tx Description'))
    objects = TransactionModelAdmin()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _l('Transaction')
        verbose_name_plural = _l('Transactions')

    def __str__(self):
        return '{x1}-{x2}/{x5}: {x3}/{x4}'.format(x1=self.account.code,
                                                  x2=self.account.name,
                                                  x3=self.amount,
                                                  x4=self.tx_type,
                                                  x5=self.account.balance_type)
