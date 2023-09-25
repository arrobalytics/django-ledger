"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import CreateUpdateMixIn


class ImportJobModelValidationError(ValidationError):
    pass


class ImportJobModelQuerySet(models.QuerySet):
    pass


class ImportJobModelManager(models.Manager):

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related(
            'bank_account_model',
            'bank_account_model__cash_account',
            'ledger_model'
        )

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(bank_account_model__entity_model__slug__exact=entity_slug) &
            (
                    Q(bank_account_model__entity_model__admin=user_model) |
                    Q(bank_account_model__entity_model__managers__in=[user_model])
            )
        )


class ImportJobModelAbstract(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    description = models.CharField(max_length=200, verbose_name=_('Description'))
    bank_account_model = models.ForeignKey('django_ledger.BankAccountModel',
                                           editable=False,
                                           on_delete=models.CASCADE,
                                           verbose_name=_('Associated Bank Account Model'))
    ledger_model = models.OneToOneField('django_ledger.LedgerModel',
                                        editable=False,
                                        on_delete=models.CASCADE,
                                        verbose_name=_('Ledger Model'),
                                        null=True,
                                        blank=True)
    completed = models.BooleanField(default=False, verbose_name=_('Import Job Completed'))
    objects = ImportJobModelManager.from_queryset(queryset_class=ImportJobModelQuerySet)()

    class Meta:
        abstract = True
        verbose_name = _('Import Job Model')
        indexes = [
            models.Index(fields=['bank_account_model']),
            models.Index(fields=['ledger_model']),
            models.Index(fields=['completed']),
        ]

    def is_configured(self):
        return all([
            self.ledger_model_id is not None,
            self.bank_account_model_id is not None
        ])

    def configure(self, commit: bool = True):
        if not self.is_configured():
            if self.ledger_model_id is None:
                self.ledger_model = self.bank_account_model.entity_model.create_ledger(
                    name=self.description
                )
            if commit:
                self.save(update_fields=[
                    'ledger_model'
                ])


class StagedTransactionModelQuerySet(models.QuerySet):
    def is_imported(self):
        return self.filter(transaction_model__isnull=True)


class StagedTransactionModelManager(models.Manager):

    def for_job(self, entity_slug: str, user_model, job_pk):
        qs = self.get_queryset()
        return qs.filter(
            Q(import_job__bank_account_model__entity__slug__exact=entity_slug) &
            (
                    Q(import_job__bank_account_model__entity__admin=user_model) |
                    Q(import_job__bank_account_model__entity__managers__in=[user_model])
            ) &
            Q(import_job__uuid__exact=job_pk)
        )


class StagedTransactionModelAbstract(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    import_job = models.ForeignKey('django_ledger.ImportJobModel', on_delete=models.CASCADE)
    fit_id = models.CharField(max_length=100)
    date_posted = models.DateField(verbose_name=_('Date Posted'))
    amount = models.DecimalField(decimal_places=2, max_digits=15, editable=False)
    name = models.CharField(max_length=200, blank=True, null=True)
    memo = models.CharField(max_length=200, blank=True, null=True)

    account_model = models.ForeignKey('django_ledger.AccountModel',
                                      on_delete=models.CASCADE,
                                      null=True,
                                      blank=True)

    transaction_model = models.OneToOneField('django_ledger.TransactionModel',
                                             on_delete=models.SET_NULL,
                                             null=True,
                                             blank=True)

    objects = StagedTransactionModelManager.from_queryset(queryset_class=StagedTransactionModelQuerySet)()

    class Meta:
        abstract = True
        verbose_name = _('Staged Transaction Model')
        indexes = [
            models.Index(fields=['import_job']),
            models.Index(fields=['date_posted']),
            models.Index(fields=['account_model']),
            models.Index(fields=['transaction_model']),
        ]

    def is_imported(self) -> bool:
        return self.transaction_model_id is not None

    def is_pending(self) -> bool:
        return self.transaction_model_id is None


class ImportJobModel(ImportJobModelAbstract):
    """
    Transaction Import Job Model Base Class.
    """


def importjobmodel_presave(instance: ImportJobModel, **kwargs):
    if instance.is_configured():
        if instance.bank_account_model.entity_model_id != instance.ledger_model.entity_id:
            raise ImportJobModelValidationError(
                message=_('Invalid Bank Account for LedgerModel. No matching Entity Model found.')
            )


pre_save.connect(importjobmodel_presave, sender=ImportJobModel)


class StagedTransactionModel(StagedTransactionModelAbstract):
    """
    Staged Transaction Model Base Class.
    """
