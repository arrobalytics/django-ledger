"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CreateUpdateMixIn, NodeTreeMixIn


class JournalEntryModelManager(models.Manager):

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


class JournalEntryModelAbstract(NodeTreeMixIn, CreateUpdateMixIn):
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
                                    on_delete=models.PROTECT,
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
                           'entity_slug': self.ledger.entity.slug
                       })

    def get_balances(self):
        txs = self.txs.only('tx_type', 'amount')
        credits = txs.filter(tx_type__iexact='credit').aggregate(Sum('amount'))
        debits = txs.filter(tx_type__iexact='debit').aggregate(Sum('amount'))
        balances = {
            'credits': credits['amount__sum'],
            'debits': debits['amount__sum']
        }
        return balances

    def je_is_valid(self):
        balances = self.get_balances()
        return balances['credits'] == balances['debits']

    def clean(self):
        check1 = 'Debits and credits do not match.'
        if not self.je_is_valid():
            raise ValidationError(check1)

    def save(self, *args, **kwargs):
        try:
            self.clean_fields()
            self.clean()
        except ValidationError as e:
            self.txs.all().delete()
            raise ValidationError(f'Something went wrong cleaning journal entry ID: {self.uuid}: {e}')
        super().save(*args, **kwargs)


class JournalEntryModel(JournalEntryModelAbstract):
    """
    Journal Entry Model Base Class From Abstract
    """
