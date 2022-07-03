"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CreateUpdateMixIn, ParentChildMixIn


class JournalEntryModelQuerySet(QuerySet):

    def create(self, verify_on_save: bool = False, **kwargs):
        obj = self.model(**kwargs)
        self._for_write = True

        # verify_on_save option avoids additional queries to validate that JE has CR/DB balanced.
        # New JEs using the create() method don't have TXS to validate.
        # therefore, it is not necessary to query DB to balance TXS.

        obj.save(force_insert=True, using=self.db, verify_txs=verify_on_save)
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
    ACTIVITIES = [
        ('op', _('Operating')),
        ('fin', _('Financing')),
        ('inv', _('Investing')),
        ('other', _('Other')),
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
    activity = models.CharField(choices=ACTIVITIES, max_length=5, verbose_name=_('Activity'))
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

    def get_absolute_url(self):
        return reverse('django_ledger:je-detail',
                       kwargs={
                           'je_pk': self.id,
                           'ledger_pk': self.ledger_id,
                           # pylint: disable=no-member
                           'entity_slug': self.ledger.entity.slug
                       })

    def get_balances(self):
        txs_qs = self.txs.order_by('tx_type').values('tx_type').annotate(
            tx_type_total=Sum('amount'))
        txs_idx = {
            i['tx_type']: i['tx_type_total'] for i in txs_qs
        }
        balances = {
            'credit': txs_idx.get('credit', Decimal('0.00')),
            'debit': txs_idx.get('debit', Decimal('0.00'))
        }
        return balances

    def je_is_valid(self):
        balances = self.get_balances()
        return balances['credit'] == balances['debit']

    def clean(self, verify_txs: bool = True):
        check1 = 'Debits and credits do not match.'
        if verify_txs:
            if not self.je_is_valid():
                raise ValidationError(check1)

    def mark_as_posted(self, commit: bool = False):
        if not self.posted:
            self.posted = True
            if commit:
                self.save(update_fields=[
                    'posted',
                    'updated'
                ])

    def mark_as_locked(self, commit: bool = False):
        if not self.locked:
            self.locked = True
            if commit:
                self.save(update_fields=[
                    'locked',
                    'updated'
                ])

    def mark_as_unlocked(self, commit: bool = False):
        if self.locked:
            self.locked = False
            if commit:
                self.save(update_fields=[
                    'locked',
                    'updated'
                ])

    def save(self, verify_txs: bool = True, *args, **kwargs):
        try:
            self.clean(verify_txs=verify_txs)
        except ValidationError as e:
            self.txs.all().delete()
            raise ValidationError(f'Something went wrong cleaning journal entry ID: {self.uuid}: {e}')
        super().save(*args, **kwargs)


class JournalEntryModel(JournalEntryModelAbstract):
    """
    Journal Entry Model Base Class From Abstract
    """
