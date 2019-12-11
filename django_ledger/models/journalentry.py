from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from django_ledger.models.mixins.base import CreateUpdateMixIn

ACTIVITIES = (
    ('op', _('Operating')),
    ('fin', _('Financing')),
    ('inv', _('Investing')),
    ('other', _('Other')),
)

ACTIVITY_ALLOWS = [a[0] for a in ACTIVITIES]


def validate_activity(act):
    if act:
        valid = act in ACTIVITY_ALLOWS
        if not valid:
            raise ValidationError(f'{act} is invalid. Choices are {ACTIVITY_ALLOWS}.')
    return act


class JournalEntryModelManager(models.Manager):

    def on_entity(self, entity):
        return self.get_queryset().filter(ledger__entity=entity)


class JournalEntryModel(CreateUpdateMixIn):
    date = models.DateField(verbose_name=_l('Date'))
    description = models.CharField(max_length=70, blank=True, null=True, verbose_name=_l('Description'))
    activity = models.CharField(choices=ACTIVITIES, max_length=5, verbose_name=_l('Activity'))
    origin = models.CharField(max_length=30, blank=True, null=True, verbose_name=_l('Origin'))
    parent = models.ForeignKey('self',
                               blank=True,
                               null=True,
                               verbose_name=_l('Parent'),
                               related_name='children',
                               on_delete=models.CASCADE)
    ledger = models.ForeignKey('django_ledger.LedgerModel',
                               verbose_name=_l('Ledger'),
                               related_name='journal_entry',
                               on_delete=models.CASCADE)
    objects = JournalEntryModelManager()

    class Meta:
        verbose_name = _l('Journal Entry')
        verbose_name_plural = _l('Journal Entries')

    class MPTTMeta:
        order_insertion_by = ['name']

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


### JournalEntryModel Signals --------
def je_presave(sender, instance, *args, **kwargs):
    try:
        instance.clean_fields()
        instance.clean()
    except ValidationError:
        instance.txs.all().delete()
        raise ValidationError('Something went wrong cleaning journal entry ID: {x1}'.format(x1=instance.id))


pre_save.connect(je_presave, sender=JournalEntryModel)
