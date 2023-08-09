from uuid import uuid4

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.mixins import CreateUpdateMixIn


class ClosingEntryModelQuerySet(models.QuerySet):
    pass


class ClosingEntryModelManager(models.Manager):
    pass


class ClosingEntryModelAbstract(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity_model = models.ForeignKey('django_ledger.EntityModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_('Entity Model'))
    account_model = models.ForeignKey('django_ledger.AccountModel',
                                      on_delete=models.RESTRICT,
                                      verbose_name=_('Account Model'))
    unit_model = models.ForeignKey('django_ledger.EntityUnitModel',
                                   null=True,
                                   blank=True,
                                   on_delete=models.RESTRICT,
                                   verbose_name=_('Entity Model'))
    closing_date = models.DateField(verbose_name=_('Closing Date'))
    activity = models.CharField(max_length=20,
                                choices=JournalEntryModel.ACTIVITIES,
                                null=True,
                                blank=True,
                                verbose_name=_('Activity'))

    balance = models.DecimalField(verbose_name=_('Closing Entry Balance'),
                                  max_digits=20,
                                  decimal_places=6)

    objects = ClosingEntryModelManager.from_queryset(queryset_class=ClosingEntryModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Closing Entry Model')
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'entity_model',
                    'account_model',
                    'closing_date',
                    'unit_model',
                    'activity'
                ],
                name='unique_closing_entry'
            )
        ]
        indexes = [
            models.Index(fields=['entity_model']),
            models.Index(fields=['account_model']),
            models.Index(fields=[
                'entity_model',
                'closing_date',
                'account_model',
                'unit_model',
                'activity'
            ])
        ]

    def __str__(self):
        return f'{self.__class__.__name__}: {self.closing_date.strftime("%D")} | {self.balance}'


class ClosingEntryModel(ClosingEntryModelAbstract):
    """
    Base ClosingEntryModel Class
    """
