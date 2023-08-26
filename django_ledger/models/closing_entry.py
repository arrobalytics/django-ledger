from uuid import uuid4, UUID

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models import lazy_loader
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
    closing_date = models.DateField(verbose_name=_('Closing Date'))
    objects = ClosingEntryModelManager.from_queryset(queryset_class=ClosingEntryModelQuerySet)()

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'entity_model',
                    'closing_date'
                ],
                name='unique_entity_closing_date',
                violation_error_message=_('Only one Closing Entry for Date Allowed.')
            )
        ]
        indexes = [
            models.Index(fields=['entity_model']),
            models.Index(fields=['closing_date']),
            models.Index(fields=['entity_model', 'closing_date'])
        ]
        ordering = ['closing_date']

    def __str__(self):
        return f'{self.__class__.__name__}: {self.entity_model.name} {self.closing_date}'


class ClosingEntryModel(ClosingEntryModelAbstract):
    pass


class ClosingEntryTransactionModelQuerySet(models.QuerySet):
    pass


class ClosingEntryTransactionModelManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related(
            'closing_entry_model',
            'closing_entry_model__entity_model'
        )

    def for_entity(self, entity_slug):
        qs = self.get_queryset()
        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return qs.filter(closing_entry_model__entity_model=entity_slug)
        elif isinstance(entity_slug, UUID):
            return qs.filter(closing_entry_model__entity_model__uuid__exact=entity_slug)
        return qs.filter(closing_entry_model__entity_model__slug__exact=entity_slug)


class ClosingEntryTransactionModelAbstract(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    closing_entry_model = models.ForeignKey('django_ledger.ClosingEntryModel',
                                            on_delete=models.CASCADE)
    account_model = models.ForeignKey('django_ledger.AccountModel',
                                      on_delete=models.RESTRICT,
                                      verbose_name=_('Account Model'))
    unit_model = models.ForeignKey('django_ledger.EntityUnitModel',
                                   null=True,
                                   blank=True,
                                   on_delete=models.RESTRICT,
                                   verbose_name=_('Entity Model'))

    activity = models.CharField(max_length=20,
                                choices=JournalEntryModel.ACTIVITIES,
                                null=True,
                                blank=True,
                                verbose_name=_('Activity'))

    balance = models.DecimalField(verbose_name=_('Closing Entry Balance'),
                                  max_digits=20,
                                  decimal_places=6)

    objects = ClosingEntryTransactionModelManager.from_queryset(queryset_class=ClosingEntryTransactionModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Closing Entry Model')
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'closing_entry_model',
                    'account_model',
                    'unit_model',
                    'activity'
                ],
                name='unique_closing_entry'
            ),
            models.UniqueConstraint(
                fields=[
                    'closing_entry_model',
                    'account_model',
                    'unit_model',
                ],
                condition=Q(activity=None),
                name='unique_ce_opt_1'
            ),
            models.UniqueConstraint(
                fields=[
                    'closing_entry_model',
                    'account_model',
                    'activity',
                ],
                condition=Q(unit_model=None),
                name='unique_ce_opt_2'
            ),
            models.UniqueConstraint(
                fields=[
                    'closing_entry_model',
                    'account_model'
                ],
                condition=Q(unit_model=None) & Q(activity=None),
                name='unique_ce_opt_3'
            )
        ]

        indexes = [
            models.Index(fields=['closing_entry_model']),
            models.Index(fields=['account_model'])
        ]

    def __str__(self):
        return f'{self.__class__.__name__}: {self.closing_entry_model.closing_date.strftime("%D")} | {self.balance}'


class ClosingEntryTransactionModel(ClosingEntryTransactionModelAbstract):
    """
    Base ClosingEntryModel Class
    """
