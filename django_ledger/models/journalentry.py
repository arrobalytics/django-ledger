from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.db.models.signals import pre_save

from .mixins import CreateUpdateMixIn

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


def validate_activity(acts):
    if acts:
        if isinstance(acts, str):
            acts = [acts]
        for act in acts:
            if act not in ACTIVITY_ALLOWS:
                raise ValidationError('{a} is invalid. Choices are {ch}'.format(ch=', '.join(ACTIVITY_ALLOWS),
                                                                                a=act))
    return acts


def validate_freq(freq):
    for freq in FREQUENCY_ALLOWS:
        if freq not in FREQUENCY_ALLOWS:
            raise ValidationError('{f} is invalid. Choices are {ch}'.format(ch=', '.join(FREQUENCY_ALLOWS),
                                                                            f=freq))
    return freq


class JournalEntryModelAbstract(CreateUpdateMixIn):
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    desc = models.CharField(max_length=70, blank=True, null=True)
    freq = models.CharField(max_length=2,
                            choices=FREQUENCY)
    activity = models.CharField(choices=ACTIVITIES,
                                max_length=5)
    origin = models.CharField(max_length=30, blank=True, null=True)

    parent = models.ForeignKey('self',
                               blank=True,
                               null=True,
                               related_name="children",
                               on_delete=models.CASCADE)

    ledger = models.ForeignKey('django_ledger.LedgerModel',
                               related_name='jes',
                               on_delete=models.CASCADE)

    class Meta:
        abstract = True
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'

    def __str__(self):
        return 'JE ID: {x1} - Desc: {x2}'.format(x1=self.pk, x2=self.desc)

    def get_balances(self):
        credits = self.txs.filter(tx_type__iexact='credit').aggregate(Sum('amount'))
        debits = self.txs.filter(tx_type__iexact='debit').aggregate(Sum('amount'))

        balances = dict()
        balances['credits'] = credits
        balances['debits'] = debits

        if credits == debits:
            balances['valid'] = True
        else:
            balances['valid'] = False
        return balances

    def je_is_valid(self):
        return self.get_balances()['valid']

    def clean(self):

        # check1 = 'JE must have either a "ledger" or "forecast" models assigned'
        # if self.ledger is None and self.actuals is None:
        #     raise ValidationError(check1)
        # elif self.forecast is not None and self.actuals is not None:
        #     raise ValidationError(check1)

        check2 = 'Debits and credits do not balance'
        if not self.je_is_valid():
            raise ValidationError(check2)

        check3 = 'Recurring JE must have an "end_date"'
        if self.freq != 'nr':
            if self.end_date is None:
                raise ValidationError(check3)
            else:
                self.end_date = self.start_date

                # todo: 'JE Series validator'
                # check4 = 'Series validator'


class JournalEntryModel(JournalEntryModelAbstract):
    """
    Final JournalEntryModel from Abstracts
    """


### JournalEntryModel Signals --------
def je_presave(sender, instance, *args, **kwargs):
    instance.clean_fields()
    instance.clean()


pre_save.connect(je_presave, sender=JournalEntryModel)
