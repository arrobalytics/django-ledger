from uuid import uuid4

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.entity import EntityModel
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
    fiscal_year = models.SmallIntegerField(verbose_name=_('Fiscal Year'))
    fiscal_month = models.SmallIntegerField(verbose_name=_('Fiscal Month'),
                                            choices=EntityModel.FY_MONTHS,
                                            null=True,
                                            blank=True)
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
                    'fiscal_year',
                    'unit_model',
                    'fiscal_month',
                    'activity'
                ],
                name='unique_ce_all'
            ),
            models.UniqueConstraint(
                fields=[
                    'entity_model',
                    'account_model',
                    'fiscal_year'
                ],
                condition=Q(unit_model=None) & Q(fiscal_month=None) & Q(activity=None),
                name='unique_ce_opt_1'
            ),
            models.UniqueConstraint(
                fields=[
                    'entity_model',
                    'account_model',
                    'fiscal_year',
                    'unit_model'
                ],
                condition=Q(fiscal_month=None) & Q(activity=None),
                name='unique_ce_opt_2'
            ),
            models.UniqueConstraint(
                fields=[
                    'entity_model',
                    'account_model',
                    'fiscal_year',
                    'fiscal_month'
                ],
                condition=Q(unit_model=None) & Q(activity=None),
                name='unique_ce_opt_3'
            ),
            models.UniqueConstraint(
                fields=[
                    'entity_model',
                    'account_model',
                    'fiscal_year',
                    'activity'
                ],
                condition=Q(unit_model=None) & Q(fiscal_month=None),
                name='unique_ce_opt_4'
            ),
            models.UniqueConstraint(
                fields=[
                    'entity_model',
                    'account_model',
                    'fiscal_year',
                    'unit_model',
                    'fiscal_month'
                ],
                condition=Q(activity=None),
                name='unique_ce_opt_5'
            ),
            models.UniqueConstraint(
                fields=[
                    'entity_model',
                    'account_model',
                    'fiscal_year',
                    'unit_model',
                    'activity'
                ],
                condition=Q(fiscal_month=None),
                name='unique_ce_opt_6'
            ),
            models.UniqueConstraint(
                fields=[
                    'entity_model',
                    'account_model',
                    'fiscal_year',
                    'fiscal_month',
                    'activity'
                ],
                condition=Q(unit_model=None),
                name='unique_ce_opt_7'
            ),
        ]
        indexes = [
            models.Index(fields=['entity_model']),
            models.Index(fields=['account_model']),
            models.Index(fields=[
                'entity_model',
                'account_model',
                'unit_model',
                'activity',
                'fiscal_year',
                'fiscal_month'
            ])
        ]

    def __str__(self):
        if self.is_fiscal_year_closing():
            return f'{self.__class__.__name__}: {self.fiscal_year} | {self.balance}'
        return f'{self.__class__.__name__}: {self.fiscal_year}/{self.fiscal_month} | {self.balance}'

    def is_fiscal_year_closing(self) -> bool:
        return self.fiscal_month is None


class ClosingEntryModel(ClosingEntryModelAbstract):
    """
    Base ClosingEntryModel Class
    """
