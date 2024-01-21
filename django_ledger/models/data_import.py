"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from decimal import Decimal
from typing import Optional, Set, Dict, List
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Count, Sum, Case, When, F, Value, DecimalField, BooleanField
from django.db.models.functions import Coalesce
from django.db.models.signals import pre_save
from django.utils.translation import gettext_lazy as _

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.utils import lazy_loader

from django_ledger.models import JournalEntryModel


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

    def for_user(self, user_model):
        qs = self.get_queryset()
        if user_model.is_superuser:
            return qs
        return qs.filter(
            Q(bank_account_model__entity_model__admin=user_model) |
            Q(bank_account_model__entity_model__managers__in=[user_model])

        )

    def for_entity(self, entity_slug: str, user_model):
        qs = self.for_user(user_model)
        return qs.filter(
            Q(bank_account_model__entity_model__slug__exact=entity_slug)
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

    def get_delete_message(self) -> str:
        return _(f'Are you sure you want to delete Import Job {self.description}?')


class StagedTransactionModelQuerySet(models.QuerySet):

    def is_pending(self):
        return self.filter(transaction_model__isnull=True)

    def is_imported(self):
        return self.filter(transaction_model__isnull=False)

    def is_parent(self):
        return self.filter(parent_id__isnull=True)

    def is_ready_to_import(self):
        return self.filter(ready_to_import=True)


class StagedTransactionModelManager(models.Manager):

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related(
            'parent',
            'account_model',
            'unit_model',
            'transaction_model',
            'transaction_model__journal_entry',
            'transaction_model__account').annotate(
            children_count=Count('split_transaction_set'),
            children_mapped_count=Count('split_transaction_set__account_model_id'),
            total_amount_split=Coalesce(
                Sum('split_transaction_set__amount_split'),
                Value(value=0.00, output_field=DecimalField())
            ),
            group_uuid=Case(
                When(parent_id__isnull=True, then=F('uuid')),
                When(parent_id__isnull=False, then=F('parent_id'))
            ),
        ).annotate(
            ready_to_import=Case(
                # is mapped singleton...
                When(
                    condition=(
                            Q(children_count__exact=0) &
                            Q(account_model__isnull=False) &
                            Q(parent__isnull=True) &
                            Q(transaction_model__isnull=True)
                    ),
                    then=True
                ),
                # is children, mapped and all parent amount is split...
                When(
                    condition=(
                            Q(children_count__gt=0) &
                            Q(children_count=F('children_mapped_count')) &
                            Q(total_amount_split__exact=F('amount')) &
                            Q(parent__isnull=True) &
                            Q(transaction_model__isnull=True)
                    ),
                    then=True
                ),
                default=False,
                output_field=BooleanField()
            ),
            can_split_into_je=Case(
                When(
                    condition=(
                            Q(children_count__gt=0) &
                            Q(children_count=F('children_mapped_count')) &
                            Q(total_amount_split__exact=F('amount')) &
                            Q(parent__isnull=True) &
                            Q(transaction_model__isnull=True)
                    ),
                    then=True
                ),
                default=False,
                output_field=BooleanField()
            )
        ).order_by(
            'date_posted',
            'group_uuid',
            '-children_count'
        )

    def for_job(self, entity_slug: str, user_model, job_pk):
        qs = self.get_queryset()
        return qs.filter(
            Q(import_job__bank_account_model__entity__slug__exact=entity_slug) &
            (
                    Q(import_job__bank_account_model__entity__admin=user_model) |
                    Q(import_job__bank_account_model__entity__managers__in=[user_model])
            ) &
            Q(import_job__uuid__exact=job_pk)
        ).prefetch_related('split_transaction_set')


class StagedTransactionModelAbstract(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    parent = models.ForeignKey('self',
                               null=True,
                               blank=True,
                               editable=False,
                               on_delete=models.CASCADE,
                               related_name='split_transaction_set',
                               verbose_name=_('Parent Transaction'))
    import_job = models.ForeignKey('django_ledger.ImportJobModel', on_delete=models.CASCADE)
    fit_id = models.CharField(max_length=100)
    date_posted = models.DateField(verbose_name=_('Date Posted'))
    bundle_split = models.BooleanField(default=True, verbose_name=_('Bundle Split Transactions'))
    activity = models.CharField(choices=JournalEntryModel.ACTIVITIES,
                                max_length=20,
                                null=True,
                                blank=True,
                                verbose_name=_('Proposed Activity'))
    amount = models.DecimalField(decimal_places=2,
                                 max_digits=15,
                                 editable=False,
                                 null=True,
                                 blank=True)
    amount_split = models.DecimalField(decimal_places=2, max_digits=15, null=True, blank=True)
    name = models.CharField(max_length=200, blank=True, null=True)
    memo = models.CharField(max_length=200, blank=True, null=True)

    account_model = models.ForeignKey('django_ledger.AccountModel',
                                      on_delete=models.RESTRICT,
                                      null=True,
                                      blank=True)

    unit_model = models.ForeignKey('django_ledger.EntityUnitModel',
                                   on_delete=models.RESTRICT,
                                   null=True,
                                   blank=True,
                                   verbose_name=_('Entity Unit Model'))

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

    def __init__(self, *args, **kwargs):
        self._activity = None
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'{self.__class__.__name__}: {self.get_amount()}'

    def from_commit_dict(self, split_amount: Optional[Decimal] = None) -> List[Dict]:
        amt = split_amount if split_amount else self.amount
        return [{
            'account': self.import_job.bank_account_model.cash_account,
            'amount': abs(amt),
            'tx_type': DEBIT if not amt < 0.00 else CREDIT,
            'description': self.name,
            'staged_tx_model': self
        }]

    def to_commit_dict(self) -> List[Dict]:
        if self.has_children():
            children_qs = self.split_transaction_set.all()
            return [{
                'account': child_txs_model.account_model,
                'amount': abs(child_txs_model.amount_split),
                'amount_staged': child_txs_model.amount_split,
                'unit_model': child_txs_model.unit_model,
                'tx_type': CREDIT if not child_txs_model.amount_split < 0.00 else DEBIT,
                'description': child_txs_model.name,
                'staged_tx_model': child_txs_model
            } for child_txs_model in children_qs]
        return [{
            'account': self.account_model,
            'amount': abs(self.amount),
            'amount_staged': self.amount,
            'unit_model': self.unit_model,
            'tx_type': CREDIT if not self.amount < 0.00 else DEBIT,
            'description': self.name,
            'staged_tx_model': self
        }]

    def commit_dict(self, split_txs: bool = False):
        if split_txs:
            to_commit = self.to_commit_dict()
            return [
                [self.from_commit_dict(split_amount=to_split['amount_staged'])[0], to_split] for to_split in to_commit
            ]
        return [self.from_commit_dict() + self.to_commit_dict()]

    def get_amount(self) -> Decimal:
        if self.is_children():
            return self.amount_split
        return self.amount

    def is_imported(self) -> bool:
        return all([
            self.account_model_id is not None,
            self.transaction_model_id is not None,
        ])

    def is_pending(self) -> bool:
        return self.transaction_model_id is None

    def is_mapped(self) -> bool:
        return self.account_model_id is not None

    def is_single(self) -> bool:
        return all([
            not self.is_children(),
            not self.has_children()
        ])

    def is_children(self) -> bool:
        return all([
            self.parent_id is not None,
        ])

    def has_activity(self) -> bool:
        return self.activity is not None

    def has_children(self) -> bool:
        if self._state.adding:
            return False
        return getattr(self, 'children_count') > 0

    def can_split(self) -> bool:
        return not self.is_children()

    def can_have_unit(self) -> bool:
        if self._state.adding:
            return False

        # no children...
        if self.is_single():
            return True

        if all([
            self.has_children(),
            self.has_activity(),
            self.are_all_children_mapped(),
            self.bundle_split is True
        ]):
            return True

        if all([
            self.is_children(),
            self.parent.bundle_split is False if self.parent_id else False
        ]):
            return True

        # if getattr(self.parent, 'can_split_into_je'):
        #     return True
        return False

    def can_have_account(self) -> bool:
        return not self.has_children()

    def can_import(self, as_split: bool = False) -> bool:
        ready_to_import = getattr(self, 'ready_to_import')
        if not ready_to_import:
            return False

        can_split_into_je = getattr(self, 'can_split_into_je')
        if can_split_into_je and as_split:
            return True
        return all([
            self.is_role_mapping_valid(raise_exception=False)
        ])

    def add_split(self, raise_exception: bool = True, commit: bool = True, n: int = 1):
        if not self.can_split():
            if raise_exception:
                raise ImportJobModelValidationError(
                    message=_(f'Staged Transaction {self.uuid} already split.')
                )
            return

        if not self.has_children():
            n += 1

        new_txs = [
            StagedTransactionModel(
                parent=self,
                import_job=self.import_job,
                fit_id=self.fit_id,
                date_posted=self.date_posted,
                amount=None,
                amount_split=Decimal('0.00'),
                name=f'SPLIT: {self.name}'
            ) for _ in range(n)
        ]

        for txs in new_txs:
            txs.clean()

        if commit:
            new_txs = StagedTransactionModel.objects.bulk_create(objs=new_txs)

        return new_txs

    def is_total_amount_split(self) -> bool:
        return self.amount == getattr(self, 'total_amount_split')

    def are_all_children_mapped(self) -> bool:
        return getattr(self, 'children_count') == getattr(self, 'children_mapped_count')

    def get_import_role_set(self) -> Optional[Set[str]]:
        if self.is_single() and self.is_mapped():
            return {self.account_model.role}
        if self.has_children():
            split_txs_qs = self.split_transaction_set.all()
            if all([txs.is_mapped() for txs in split_txs_qs]):
                return set([txs.account_model.role for txs in split_txs_qs if txs.account_model.role != ASSET_CA_CASH])

    def get_prospect_je_activity_try(self, raise_exception: bool = True, force_update: bool = False) -> Optional[str]:
        ready_to_import = getattr(self, 'ready_to_import')
        if (not self.has_activity() and ready_to_import) or force_update:
            JournalEntryModel = lazy_loader.get_journal_entry_model()
            role_set = self.get_import_role_set()
            if role_set is not None:
                try:
                    self.activity = JournalEntryModel.get_activity_from_roles(role_set=role_set)
                    self.save(update_fields=['activity'])
                    return self.activity
                except ValidationError as e:
                    if raise_exception:
                        raise e
        return self.activity

    def get_prospect_je_activity(self) -> Optional[str]:
        return self.get_prospect_je_activity_try(raise_exception=False)

    def get_prospect_je_activity_display(self) -> Optional[str]:
        activity = self.get_prospect_je_activity_try(raise_exception=False)
        if activity is not None:
            JournalEntryModel = lazy_loader.get_journal_entry_model()
            return JournalEntryModel.MAP_ACTIVITIES[activity]

    def is_role_mapping_valid(self, raise_exception: bool = False) -> bool:
        if not self.has_activity():
            try:
                activity = self.get_prospect_je_activity_try(raise_exception=raise_exception)
                if activity is None:
                    return False
                self.activity = activity
                return True
            except ValidationError as e:
                if raise_exception:
                    raise e
                return False
        return True

    def migrate(self, split_txs: bool = False):
        if self.can_import(as_split=split_txs):
            commit_dict = self.commit_dict(split_txs=split_txs)
            import_job = self.import_job
            ledger_model = import_job.ledger_model

            if len(commit_dict):
                for je_data in commit_dict:
                    unit_model = self.unit_model if not split_txs else commit_dict[0][1]['unit_model']
                    je_model, txs_models = ledger_model.commit_txs(
                        je_timestamp=self.date_posted,
                        je_unit_model=unit_model,
                        je_txs=je_data,
                        je_desc=self.memo,
                        je_posted=False,
                        force_je_retrieval=False
                    )
                    staged_to_save = [i['staged_tx_model'] for i in je_data]
                    for i in staged_to_save:
                        i.save(update_fields=['transaction_model'])

    def clean(self, verify: bool = False):
        if self.has_children():
            self.amount_split = None
            self.account_model = None
        elif self.is_children():
            self.amount = None

        if not self.can_have_unit():
            if self.parent_id:
                self.unit_model = self.parent.unit_model

        if verify:
            self.is_role_mapping_valid(raise_exception=True)


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
