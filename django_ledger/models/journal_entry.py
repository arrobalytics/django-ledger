"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from decimal import Decimal
from typing import Set
from uuid import uuid4

from django.core.exceptions import FieldError
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, QuerySet
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.exceptions import JournalEntryValidationError
from django_ledger.io.roles import (ASSET_CA_CASH, GROUP_CFS_INVESTING_PPE, GROUP_CFS_INVESTING_SECURITIES,
                                    GROUP_CFS_FIN_DIVIDENDS, GROUP_CFS_FIN_ISSUING_EQUITY,
                                    GROUP_CFS_FIN_LT_DEBT_PAYMENTS, GROUP_CFS_FIN_ST_DEBT_PAYMENTS,
                                    GROUP_CFS_INVESTING_AND_FINANCING)
from django_ledger.models import CreateUpdateMixIn, ParentChildMixIn


class JournalEntryModelQuerySet(QuerySet):

    def create(self, verify_on_save: bool = False, **kwargs):
        is_posted = kwargs.get('posted')
        if is_posted:
            raise FieldError('Cannot create Journal Entries as posted')

        obj = self.model(**kwargs)
        self._for_write = True
        # verify_on_save option avoids additional queries to validate the journal entry.
        # New JEs using the create() method don't have any transactions to validate.
        # therefore, it is not necessary to query DB to balance TXS.
        obj.save(force_insert=True, using=self.db, verify=verify_on_save)
        return obj


class JournalEntryModelManager(models.Manager):

    def get_queryset(self):
        return JournalEntryModelQuerySet(
            self.model,
            using=self._db
        )

    def for_entity(self, entity_slug: str, user_model):
        return self.get_queryset().filter(
            Q(ledger__entity__slug__iexact=entity_slug) &
            (
                    Q(ledger__entity__admin=user_model) |
                    Q(ledger__entity__managers__in=[user_model])
            )

        )

    def for_ledger(self, ledger_pk: str, entity_slug: str, user_model):
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(ledger__uuid__exact=ledger_pk)


class JournalEntryModelAbstract(ParentChildMixIn, CreateUpdateMixIn):
    ACTIVITY_IGNORE = ['all']
    OPERATING_ACTIVITY = 'op'
    FINANCING_ACTIVITY = 'fin'
    INVESTING_ACTIVITY = 'inv'
    ACTIVITIES = [
        (OPERATING_ACTIVITY, _('Operating')),
        (FINANCING_ACTIVITY, _('Financing')),
        (INVESTING_ACTIVITY, _('Investing'))
    ]

    ACTIVITY_ALLOWS = [a[0] for a in ACTIVITIES]
    parent = models.ForeignKey('self',
                               blank=True,
                               null=True,
                               verbose_name=_('Parent Journal Entry'),
                               related_name='children',
                               on_delete=models.CASCADE)

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    date = models.DateField(verbose_name=_('Date'))
    description = models.CharField(max_length=70, blank=True, null=True, verbose_name=_('Description'))
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel',
                                    on_delete=models.RESTRICT,
                                    blank=True,
                                    null=True,
                                    verbose_name=_('Associated Entity Unit'))
    activity = models.CharField(choices=ACTIVITIES,
                                max_length=5,
                                null=True,
                                blank=True,
                                editable=False,
                                verbose_name=_('Activity'))
    origin = models.CharField(max_length=30, blank=True, null=True, verbose_name=_('Origin'))
    posted = models.BooleanField(default=False, verbose_name=_('Posted'))
    locked = models.BooleanField(default=False, verbose_name=_('Locked'))
    ledger = models.ForeignKey('django_ledger.LedgerModel',
                               verbose_name=_('Ledger'),
                               related_name='journal_entries',
                               on_delete=models.CASCADE)

    on_coa = JournalEntryModelManager()
    objects = JournalEntryModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Journal Entry')
        verbose_name_plural = _('Journal Entries')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['activity']),
            models.Index(fields=['parent']),
            models.Index(fields=['entity_unit']),
            models.Index(fields=['ledger', 'posted']),
            models.Index(fields=['locked']),
        ]

    def __str__(self):
        return 'JE ID: {x1} - Desc: {x2}'.format(x1=self.pk, x2=self.description)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._verified = False

    def is_verified(self) -> bool:
        return self._verified

    def get_absolute_url(self):
        return reverse('django_ledger:je-detail',
                       kwargs={
                           'je_pk': self.id,
                           'ledger_pk': self.ledger_id,
                           # pylint: disable=no-member
                           'entity_slug': self.ledger.entity.slug
                       })

    def get_entity_unit_name(self, no_unit_name: str = ''):
        if self.entity_unit_id:
            return self.entity_unit.name
        return no_unit_name

    def can_post(self, ignore_verify: bool = True) -> bool:
        return all([
            not self.locked,
            not self.posted,
            self.is_verified() if not ignore_verify else True
        ])

    def can_unpost(self):
        return all([
            not self.locked,
            self.posted
        ])

    def can_lock(self):
        return all([
            not self.locked
        ])

    def can_unlock(self):
        return all([
            self.locked
        ])

    def mark_as_posted(self,
                       commit: bool = False,
                       verify: bool = False,
                       raise_exception: bool = False,
                       **kwargs):
        if verify:
            self.verify()

        if not self.can_post(ignore_verify=False):
            if raise_exception:
                raise JournalEntryValidationError(f'Journal Entry {self.uuid} cannot be posted.'
                                                  f' Is verified: {self.is_verified()}')
        else:
            self.posted = True
            if commit:
                self.save(verify=False,
                          update_fields=[
                              'posted',
                              'updated'
                          ])

    def mark_as_unposted(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        if not self.can_unpost():
            if raise_exception:
                raise JournalEntryValidationError(f'Journal Entry {self.uuid} is unposted.')
        else:
            self.posted = False
            if commit:
                self.save(verify=False,
                          update_fields=[
                              'posted',
                              'updated'
                          ])

    def mark_as_locked(self, commit: bool = False, raise_exception: bool = False, **kwargs):

        if not self.can_lock():
            if raise_exception:
                raise ValidationError(f'Journal Entry {self.uuid} is already locked.')
        else:
            self.locked = True
            if commit:
                self.save(verify=False,
                          update_fields=[
                              'locked',
                              'updated'
                          ])

    def mark_as_unlocked(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        if not self.can_unlock():
            if raise_exception:
                raise ValidationError(f'Journal Entry {self.uuid} is already unlocked.')
        else:
            self.locked = False
            if commit:
                self.save(verify=False,
                          update_fields=[
                              'locked',
                              'updated'
                          ])

    def get_txs_qs(self, select_accounts: bool = True):
        if not select_accounts:
            return self.txs.all()
        return self.txs.all().select_related('account')

    def get_txs_balances(self, txs_qs=None):
        if not txs_qs:
            txs_qs = self.get_txs_qs()
        balances = txs_qs.values('tx_type').annotate(
            amount__sum=Coalesce(Sum('amount'),
                                 Decimal('0.00'),
                                 output_field=models.DecimalField()))
        return balances

    def get_txs_roles(self, txs_qs=None, exclude_cash_role: bool = False) -> Set:
        if not txs_qs:
            txs_qs = self.get_txs_qs()

        # todo: implement distinct for non SQLite Backends...
        if exclude_cash_role:
            roles_involved = [i.account.role for i in txs_qs if i.account.role != ASSET_CA_CASH]
        else:
            roles_involved = [i.account.role for i in txs_qs]
        return set(roles_involved)

    def is_balance_valid(self, txs_qs=None):
        if len(txs_qs) > 0:
            balances = self.get_txs_balances(txs_qs=txs_qs)
            bal_idx = {i['tx_type']: i['amount__sum'] for i in balances}
            return bal_idx['credit'] == bal_idx['debit']
        return True

    def is_cash_involved(self, txs_qs=None):
        return ASSET_CA_CASH in self.get_txs_roles(txs_qs=None)

    def verify(self,
               txs_qs=None,
               force_verify: bool = False,
               raise_exception: bool = True,
               **kwargs):
        if not self.is_verified() or force_verify:
            txs_qs = self.get_txs_qs()

            if not len(txs_qs):
                if raise_exception:
                    raise JournalEntryValidationError('Journal entry has no transactions.')

            if len(txs_qs) < 2:
                if raise_exception:
                    raise JournalEntryValidationError('At least two transactions required.')

            # CREDIT/DEBIT Balance validation...
            balance_is_valid = self.is_balance_valid(txs_qs)
            if not balance_is_valid:
                if raise_exception:
                    raise JournalEntryValidationError('Debits and credits do not match.')

            # activity flag...
            cash_is_involved = self.is_cash_involved(txs_qs)
            if not cash_is_involved:
                self.activity = None
            else:
                roles_involved = self.get_txs_roles(txs_qs, exclude_cash_role=True)

                # determining if investing....
                is_investing_for_ppe = all([r in GROUP_CFS_INVESTING_PPE for r in roles_involved])
                is_investing_for_securities = all([r in GROUP_CFS_INVESTING_SECURITIES for r in roles_involved])

                # determining if financing...
                is_financing_dividends = all([r in GROUP_CFS_FIN_DIVIDENDS for r in roles_involved])
                is_financing_issuing_equity = all([r in GROUP_CFS_FIN_ISSUING_EQUITY for r in roles_involved])
                is_financing_st_debt = all([r in GROUP_CFS_FIN_ST_DEBT_PAYMENTS for r in roles_involved])
                is_financing_lt_debt = all([r in GROUP_CFS_FIN_LT_DEBT_PAYMENTS for r in roles_involved])

                is_operational = all([r not in GROUP_CFS_INVESTING_AND_FINANCING for r in roles_involved])

                if sum([
                    is_investing_for_ppe,
                    is_investing_for_securities,
                    is_financing_lt_debt,
                    is_financing_st_debt,
                    is_financing_issuing_equity,
                    is_financing_dividends,
                    is_operational
                ]) > 1:
                    if raise_exception:
                        raise JournalEntryValidationError(f'Multiple activities detected in roles JE {roles_involved}.')
                else:
                    if any([
                        is_investing_for_ppe,
                        is_investing_for_securities
                    ]):
                        self.activity = self.INVESTING_ACTIVITY
                    elif any([
                        is_financing_issuing_equity,
                        is_financing_dividends,
                        is_financing_st_debt,
                        is_financing_lt_debt
                    ]):
                        self.activity = self.FINANCING_ACTIVITY
                    elif is_operational:
                        self.activity = self.OPERATING_ACTIVITY
                    else:
                        if raise_exception:
                            raise JournalEntryValidationError(f'No activity match for roles {roles_involved}.'
                                                              'Split into multiple Journal Entries or check'
                                                              ' your account selection.')
            self._verified = True
            return txs_qs
        self._verified = False

    def clean(self, verify: bool = False):
        if verify:
            txs_qs = self.verify()
            return txs_qs

    def save(self, verify: bool = False, post_on_verify: bool = False, *args, **kwargs):
        try:
            if verify:
                self.clean(verify=verify)
                if self.is_verified() and post_on_verify:
                    # commit is False since the super call takes place at the end of save()
                    self.mark_as_posted(commit=False, raise_exception=True)
        except ValidationError as e:
            if self.can_unpost():
                self.mark_as_unposted(raise_exception=True)
            raise JournalEntryValidationError(
                f'Something went wrong validating journal entry ID: {self.uuid}: {e.message}')
        except:
            # safety net, for any unexpected error...
            # no JE can be posted if not fully validated...
            self.posted = False
            self._verified = False
            self.save(updade_fields=['posted', 'updated'], verify=False)
            raise JournalEntryValidationError(f'Unknown error posting JE {self.uuid}')
        super(JournalEntryModelAbstract, self).save(*args, **kwargs)


class JournalEntryModel(JournalEntryModelAbstract):
    """
    Journal Entry Model Base Class From Abstract
    """
