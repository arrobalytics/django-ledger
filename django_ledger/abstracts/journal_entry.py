from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from mptt.models import MPTTModel

from django_ledger.abstracts.mixins import CreateUpdateMixIn

ACTIVITIES = [
    ('op', _('Operating')),
    ('fin', _('Financing')),
    ('inv', _('Investing')),
    ('other', _('Other')),
]

ACTIVITY_ALLOWS = [a[0] for a in ACTIVITIES]
ACTIVITY_IGNORE = ['all']


def validate_activity(act: str, raise_404: bool = False):
    if act:

        if act in ACTIVITY_IGNORE:
            act = None

        # todo: temporary fix. User should be able to pass a list.
        if isinstance(act, list) and len(act) == 1:
            act = act[0]
        elif isinstance(act, list) and len(act) > 1:
            exception = ValidationError(f'Multiple activities passed {act}')
            if raise_404:
                raise Http404(exception)
            raise exception

        valid = act in ACTIVITY_ALLOWS
        if act and not valid:
            exception = ValidationError(f'{act} is invalid. Choices are {ACTIVITY_ALLOWS}.')
            if raise_404:
                raise Http404(exception)
            raise exception

    return act


class JournalEntryModelManager(models.Manager):

    def for_user(self, user):
        return self.get_queryset().filter(
            Q(ledger__entity__admin=user) |
            Q(ledger__entity__managers__exact=user)
        )

    def all_posted(self):
        return self.get_queryset().filter(
            posted=True,
            ledger__posted=True
        )

    def on_entity(self, entity):
        if isinstance(entity, str):
            qs = self.get_queryset().filter(ledger__entity__slug__exact=entity)
        else:
            qs = self.get_queryset().filter(ledger__entity=entity)
        return qs

    def on_entity_posted(self, entity):
        return self.on_entity(entity=entity).filter(
            posted=True,
            ledger__posted=True
        )

    def on_ledger(self, ledger):
        if isinstance(ledger, str):
            qs = self.get_queryset().filter(ledger__slug__exact=ledger)
        else:
            qs = self.get_queryset().filter(ledger=ledger)
        return qs

    def on_ledger_posted(self, ledger):
        return self.on_ledger(ledger=ledger).filter(
            posted=True,
            ledger__posted=True
        )


class JournalEntryModelAbstract(MPTTModel, CreateUpdateMixIn):
    date = models.DateField(verbose_name=_l('Date'))
    description = models.CharField(max_length=70, blank=True, null=True, verbose_name=_l('Description'))
    activity = models.CharField(choices=ACTIVITIES, max_length=5, verbose_name=_l('Activity'))
    origin = models.CharField(max_length=30, blank=True, null=True, verbose_name=_l('Origin'))
    posted = models.BooleanField(default=False, verbose_name=_l('Posted'))
    locked = models.BooleanField(default=False, verbose_name=_l('Locked'))
    parent = models.ForeignKey('self',
                               blank=True,
                               null=True,
                               verbose_name=_l('Parent'),
                               related_name='children',
                               on_delete=models.CASCADE)
    ledger = models.ForeignKey('django_ledger.LedgerModel',
                               verbose_name=_l('Ledger'),
                               related_name='journal_entries',
                               on_delete=models.CASCADE)
    on_coa = JournalEntryModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _l('Journal Entry')
        verbose_name_plural = _l('Journal Entries')

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
        except ValidationError:
            self.txs.all().delete()
            raise ValidationError('Something went wrong cleaning journal entry ID: {x1}'.format(x1=instance.id))
        super().save(*args, **kwargs)
