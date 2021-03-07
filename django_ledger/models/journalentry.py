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
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel

# todo: this is creating a circular reference need to resolve.
# from django_ledger.abstracts.mixins import CreateUpdateMixIn

ACTIVITIES = [
    ('op', _('Operating')),
    ('fin', _('Financing')),
    ('inv', _('Investing')),
    ('other', _('Other')),
]

ACTIVITY_ALLOWS = [a[0] for a in ACTIVITIES]
ACTIVITY_IGNORE = ['all']


def validate_activity(activity: str, raise_404: bool = False):
    if activity:

        if activity in ACTIVITY_IGNORE:
            activity = None

        # todo: temporary fix. User should be able to pass a list.
        if isinstance(activity, list) and len(activity) == 1:
            activity = activity[0]
        elif isinstance(activity, list) and len(activity) > 1:
            exception = ValidationError(f'Multiple activities passed {activity}')
            if raise_404:
                raise Http404(exception)
            raise exception

        valid = activity in ACTIVITY_ALLOWS
        if activity and not valid:
            exception = ValidationError(f'{activity} is invalid. Choices are {ACTIVITY_ALLOWS}.')
            if raise_404:
                raise Http404(exception)
            raise exception

    return activity


class JournalEntryModelManager(models.Manager):

    def for_ledger(self, ledger_pk: str, entity_slug: str, user_model):
        qs = self.get_queryset().filter(
            Q(ledger__uuid__exact=ledger_pk) &
            Q(ledger__entity__slug__iexact=entity_slug) &
            (
                    Q(ledger__entity__admin=user_model) |
                    Q(ledger__entity__managers__in=[user_model])
            )

        )
        return qs


class JournalEntryModelAbstract(MPTTModel):
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

    # todo: must come from create/update mixin. Resolve circular reference.
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    on_coa = JournalEntryModelManager()

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

    class MPTTMeta:
        order_insertion_by = ['created']

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
