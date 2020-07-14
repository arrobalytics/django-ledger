from uuid import uuid4

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import CreateUpdateMixIn


class ImportJobModelManager(models.Manager):
    pass


class ImportJobModelAbstract(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    description = models.CharField(max_length=200, verbose_name=_('Description'))

    ledger = models.ForeignKey('django_ledger.LedgerModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Ledger'))

    objects = ImportJobModelManager()

    class Meta:
        abstract = True
        verbose_name = _('Import Job Model')
        indexes = [
            models.Index(fields=['ledger'])
        ]

    def status(self):
        return 'In progress..'


class StagedTransactionModelManager(models.Manager):

    def for_job(self, entity_slug: str, user_model, job_pk):
        qs = self.get_queryset()
        return qs.filter(
            Q(import_job__ledger__entity__slug__exact=entity_slug) &
            (
                    Q(import_job__ledger__entity__admin=user_model) |
                    Q(import_job__ledger__entity__managers__in=[user_model])
            ) &
            Q(import_job__uuid__exact=job_pk)
        )


class StagedTransactionModelAbstract(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    import_job = models.ForeignKey('django_ledger.ImportJobModel',
                                   on_delete=models.CASCADE)
    earnings_account = models.ForeignKey('django_ledger.AccountModel',
                                         on_delete=models.CASCADE,
                                         null=True,
                                         blank=True)
    fitid = models.CharField(max_length=100)
    amount = models.DecimalField(decimal_places=2, max_digits=15)
    date_posted = models.DateField()

    name = models.CharField(max_length=200, blank=True, null=True)
    memo = models.CharField(max_length=200, blank=True, null=True)

    tx = models.OneToOneField('django_ledger.TransactionModel',
                              on_delete=models.SET_NULL,
                              null=True,
                              blank=True)

    objects = StagedTransactionModelManager()

    class Meta:
        abstract = True
        verbose_name = _('Staged Transaction Model')
        indexes = [
            models.Index(fields=['import_job'])
        ]


class ImportJobModel(ImportJobModelAbstract):
    """
    Transaction Import Job Model Base Class.
    """


class StagedTransactionModel(StagedTransactionModelAbstract):
    """
    Staged Transaction Model Base Class.
    """
