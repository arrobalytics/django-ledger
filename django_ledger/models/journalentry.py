from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.db.models.signals import pre_save
from django.urls import reverse

from django_ledger.models.mixins.base import CreateUpdateMixIn

ACTIVITIES = (
    ('op', 'Operating'),
    ('fin', 'Financing'),
    ('inv', 'Investing'),
    ('other', 'Other'),
)

ACTIVITY_ALLOWS = [a[0] for a in ACTIVITIES]

FREQUENCY = (
    ('nr', 'Non-Recurring'),
    ('d', 'Daily'),
    ('m', 'Monthly'),
    ('q', 'Quarterly'),
    ('y', 'Yearly'),
    ('sm', 'Monthly Series'),
    ('sy', 'Yearly Series'),
)

FREQUENCY_ALLOWS = [f[0] for f in FREQUENCY]


def validate_activity(act):
    if act:
        valid = act in ACTIVITY_ALLOWS
        if not valid:
            raise ValidationError(f'{act} is invalid. Choices are {ACTIVITY_ALLOWS}.')
    return act


def validate_freq(freq):
    valid_freq = freq in FREQUENCY_ALLOWS
    if not valid_freq:
        raise ValidationError(f'{freq} is invalid. Choices are {FREQUENCY_ALLOWS}.')
    return freq


class JournalEntryModelManager(models.Manager):

    def on_entity(self, entity):
        return self.get_queryset().filter(ledger__entity=entity)


class JournalEntryModel(CreateUpdateMixIn):
    date = models.DateField()
    description = models.CharField(max_length=70, blank=True, null=True)
    activity = models.CharField(choices=ACTIVITIES, max_length=5)
    origin = models.CharField(max_length=30, blank=True, null=True)
    parent = models.ForeignKey('self',
                               blank=True,
                               null=True,
                               related_name='children',
                               on_delete=models.CASCADE)
    ledger = models.ForeignKey('django_ledger.LedgerModel',
                               related_name='journal_entry',
                               on_delete=models.CASCADE)

    objects = JournalEntryModelManager()

    class Meta:
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'

    def __str__(self):
        return 'JE ID: {x1} - Desc: {x2}'.format(x1=self.pk, x2=self.description)

    def get_absolute_url(self):
        return reverse('django_ledger:journal-entry-detail',
                       kwargs={
                           'je_pk': self.id,
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
        check1 = 'Debits and credits do not balance'
        if not self.je_is_valid():
            raise ValidationError(check1)


### JournalEntryModel Signals --------
def je_presave(sender, instance, *args, **kwargs):
    try:
        instance.clean_fields()
        instance.clean()
    except ValidationError:
        instance.txs.all().delete()
        raise ValidationError('Something went wrong cleaning journal entry ID:{x1}'.format(x1=instance.id))


pre_save.connect(je_presave, sender=JournalEntryModel)
