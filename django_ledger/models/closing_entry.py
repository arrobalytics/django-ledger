from django.db import models
from django_ledger.models.mixins import CreateUpdateMixIn
from django.utils.translation import ugettext_lazy as _
from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.entity import EntityModel
from uuid import uuid4


class ClosingEntryModelAbstract(CreateUpdateMixIn):

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity_model = models.ForeignKey('django_ledger.EntityModel', on_delete=models.CASCADE, verbose_name=_('Entity Model'))
    account_model = models.ForeignKey('django_ledger.AccountModel', on_delete=models.RESTRICT, verbose_name=_('Account Model'))
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel', on_delete=models.RESTRICT, verbose_name=_('Entity Model'))
    fiscal_year = models.SmallIntegerField(verbose_name=_('Fiscal Year'))
    fiscal_month = models.SmallIntegerField(verbose_name=_('Fiscal Month'), choices=EntityModel.FY_MONTHS, null=True, blank=True)
    activity = models.CharField(max_length=20, choices=JournalEntryModel.ACTIVITIES, null=True, blank=True, verbose_name=_('Activity'))
    balance = models.DecimalField(verbose_name=_('Closing Entry Balance'))

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Closing Entry Model')        
        indexes = [
            models.Index(fields=['entity_model']),
            models.Index(fields=['account_model']),
            models.Index(fields=[
                'entity_model',
                'account_model',
                'entity_unit',
                'activity',
                'fiscal_year',
                'fiscal_month'
            ])
        ]