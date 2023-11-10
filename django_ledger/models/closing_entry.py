from decimal import Decimal
from itertools import groupby, chain
from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save, pre_delete
from django.urls import reverse
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _

from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.mixins import CreateUpdateMixIn, MarkdownNotesMixIn
from django_ledger.models.transactions import TransactionModel
from django_ledger.models.utils import lazy_loader


class ClosingEntryValidationError(ValidationError):
    pass


class ClosingEntryModelQuerySet(models.QuerySet):

    def posted(self):
        return self.filter(posted=True)

    def not_posted(self):
        return self.filter(posted=False)


class ClosingEntryModelManager(models.Manager):

    def for_entity(self, entity_slug, user_model):
        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return self.get_queryset().filter(
                Q(entity_model=entity_slug) &
                (
                        Q(entity_model__admin=user_model) |
                        Q(entity_model__managers__in=[user_model])
                )

            )
        return self.get_queryset().filter(
            Q(entity_model__slug__exact=entity_slug) &
            (
                    Q(entity_model__admin=user_model) |
                    Q(entity_model__managers__in=[user_model])
            )

        )


class ClosingEntryModelAbstract(CreateUpdateMixIn, MarkdownNotesMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity_model = models.ForeignKey('django_ledger.EntityModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_('Entity Model'))
    ledger_model = models.OneToOneField('django_ledger.LedgerModel', on_delete=models.CASCADE)
    closing_date = models.DateField(verbose_name=_('Closing Date'))
    posted = models.BooleanField(default=False, verbose_name=_('Is Posted'))
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
            models.Index(fields=['posted']),
            models.Index(fields=['entity_model', 'posted', 'closing_date'])
        ]
        ordering = ['-closing_date']

    def __str__(self):
        return f'{self.__class__.__name__}: {self.entity_model.name} {self.closing_date}'

    def is_posted(self) -> bool:
        return self.posted is True

    def get_closing_date_as_timestamp(self):
        return make_aware(datetime.combine(self.closing_date, time.max))

    def migrate(self):
        ce_txs = self.closingentrytransactionmodel_set.all().order_by(
            'tx_type',
            'account_model',
            'unit_model',
        )
        ce_txs_gb = groupby(ce_txs, key=lambda k: k.tx_type)
        ce_txs_gb = {k: list(l) for k, l in ce_txs_gb}
        ce_txs_sum = {k: sum(v.balance for v in l) for k, l in ce_txs_gb.items()}

        if len(ce_txs_sum) and ce_txs_sum[TransactionModel.DEBIT] != ce_txs_sum[TransactionModel.CREDIT]:
            raise ClosingEntryValidationError(
                message=f'Invalid transactions. Credits {ce_txs_sum[TransactionModel.CREDIT]} '
                        f'do not equal Debits {ce_txs_sum[TransactionModel.DEBIT]}'
            )

        ce_txs = list(ce_txs)
        key_func = lambda i: (
            str(i.unit_model_id) if i.unit_model_id else '',
            i.activity if i.activity else ''
        )
        ce_txs.sort(key=key_func)
        ce_txs_gb = groupby(ce_txs, key=key_func)
        ce_txs_gb = {
            unit_model_id: list(je_txs) for unit_model_id, je_txs in ce_txs_gb
        }

        ce_txs_journal_entries = {
            (unit_model_id, activity): JournalEntryModel(
                ledger=self.ledger_model,
                timestamp=self.get_closing_date_as_timestamp(),
                activity=activity if activity else None,
                entity_unit_id=unit_model_id if unit_model_id else None,
                origin='closing_entry',
                description=f'Closing Entry {self.closing_date}',
                is_closing_entry=True,
                posted=True,
                locked=True
            ) for (unit_model_id, activity), je_txs in ce_txs_gb.items()
        }

        ce_je_txs = {
            (unit_model_id, activity): [
                TransactionModel(
                    journal_entry=ce_txs_journal_entries[(unit_model_id, activity)],
                    tx_type=tx.tx_type,
                    account=tx.account_model,
                    amount=tx.balance
                ) for tx in je_txs
            ] for (unit_model_id, activity), je_txs in ce_txs_gb.items()
        }

        JournalEntryModel.objects.bulk_create(objs=chain([l for _, l in ce_txs_journal_entries.items()]))
        TransactionModel.objects.bulk_create(objs=chain.from_iterable([l for _, l in ce_je_txs.items()]))

        for k, je_model in ce_txs_journal_entries.items():
            je_model.save(verify=True)

        return ce_txs_journal_entries, ce_je_txs

    def create_entry_ledger(self, commit: bool = False):
        if self.ledger_model_id is None:
            ledger_model = LedgerModel(
                name=f'Closing Entry {self.closing_date} Ledger',
                entity_id=self.entity_model_id,
                hidden=True,
                locked=True,
                posted=True
            )
            ledger_model.clean()
            ledger_model.save()
            self.ledger_model = ledger_model

            if commit:
                self.save(update_fields=[
                    'ledger_model',
                    'updated'
                ])

    # ACTIONS POST...
    def can_post(self) -> bool:
        return not self.is_posted()

    def mark_as_posted(self, commit: bool = False, **kwargs):
        if not self.can_post():
            raise ClosingEntryValidationError(
                message=_(f'Closing Entry {self.closing_date} is already posted.')
            )

        self.migrate()
        self.posted = True
        if commit:
            self.save(update_fields=[
                'posted',
                'ledger_model',
                'updated'
            ])
            self.entity_model.save_closing_entry_dates_meta(commit=True)

    def get_mark_as_posted_html_id(self) -> str:
        return f'closing_entry_post_{self.uuid}'

    def get_mark_as_posted_message(self):
        return _(f'Are you sure you want to post Closing Entry dated {self.closing_date}?')

    def get_mark_as_posted_url(self, entity_slug: Optional[str] = None) -> str:
        if not entity_slug:
            entity_slug = self.entity_model.slug
        return reverse(viewname='django_ledger:closing-entry-action-mark-as-posted',
                       kwargs={
                           'entity_slug': entity_slug,
                           'closing_entry_pk': self.uuid
                       })

    # ACTION UNPOST...
    def can_unpost(self) -> bool:
        return self.is_posted()

    def mark_as_unposted(self, commit: bool = False, **kwargs):
        if not self.can_unpost():
            raise ClosingEntryValidationError(
                message=_(f'Closing Entry {self.closing_date} is not posted.')
            )
        self.posted = False
        TransactionModel.objects.for_ledger(
            ledger_model=self.ledger_model,
            entity_slug=self.entity_model_id
        ).delete()
        self.ledger_model.journal_entries.all().delete()
        if commit:
            self.save(update_fields=[
                'posted',
                'ledger_model',
                'updated'
            ])
            self.entity_model.save_closing_entry_dates_meta(commit=True)

    def get_mark_as_unposted_html_id(self) -> str:
        return f'closing_entry_unpost_{self.uuid}'

    def get_mark_as_unposted_message(self):
        return _(f'Are you sure you want to unpost Closing Entry dated {self.closing_date}?')

    def get_mark_as_unposted_url(self, entity_slug: Optional[str] = None) -> str:
        if not entity_slug:
            entity_slug = self.entity_model.slug
        return reverse(viewname='django_ledger:closing-entry-action-mark-as-unposted',
                       kwargs={
                           'entity_slug': entity_slug,
                           'closing_entry_pk': self.uuid
                       })

    # ACTION CAN UPDATE TXS...
    def can_update_txs(self) -> bool:
        return not self.is_posted()

    def update_transactions(self, force_update: bool = False, commit: bool = True, **kwargs):
        if not self.can_update_txs():
            raise ClosingEntryValidationError(
                message=_('Cannot update transactions of a posted Closing Entry.')
            )
        entity_model = self.entity_model
        entity_model.close_entity_books(
            closing_entry_model=self,
            force_update=force_update,
            commit=commit
        )

    def get_update_transactions_html_id(self) -> str:
        return f'closing_entry_update_txs_{self.uuid}'

    def get_update_transactions_message(self):
        return _(f'Are you sure you want to update all Closing Entry {self.closing_date} transactions? '
                 'This action will delete existing closing entry transactions and create new ones.')

    def get_update_transactions_url(self, entity_slug: Optional[str] = None) -> str:
        if not entity_slug:
            entity_slug = self.entity_model.slug
        return reverse(viewname='django_ledger:closing-entry-action-update-txs',
                       kwargs={
                           'entity_slug': entity_slug,
                           'closing_entry_pk': self.uuid
                       })

    # DELETE...
    def can_delete(self):
        return not self.is_posted()

    def delete(self, **kwargs):
        if not self.can_delete():
            raise ClosingEntryValidationError(
                message=_('Cannot delete a posted Closing Entry')
            )
        TransactionModel.objects.for_ledger(
            ledger_model=self.ledger_model,
            entity_slug=self.entity_model_id
        ).delete()
        return self.ledger_model.delete()

    def get_delete_html_id(self) -> str:
        return f'closing_entry_delete_txs_{self.uuid}'

    def get_delete_message(self):
        return _(f'Are you sure you want to delete Closing Entry {self.closing_date}? '
                 'This action cannot be undone.')

    def get_delete_url(self, entity_slug: Optional[str] = None) -> str:
        if not entity_slug:
            entity_slug = self.entity_model.slug
        return reverse(viewname='django_ledger:closing-entry-action-delete',
                       kwargs={
                           'entity_slug': entity_slug,
                           'closing_entry_pk': self.uuid
                       })

    # HTML Tags....
    def get_html_id(self):
        return f'closing_entry_{self.uuid}'

    # URLs Generation...
    def get_list_url(self):
        return reverse(
            viewname='django_ledger:closing-entry-list',
            kwargs={
                'entity_slug': self.entity_model.slug
            }
        )


class ClosingEntryModel(ClosingEntryModelAbstract):
    pass


class ClosingEntryTransactionModelQuerySet(models.QuerySet):
    pass


class ClosingEntryTransactionModelManager(models.Manager):

    # def get_queryset(self):
    #     return super().get_queryset().select_related(
    #         'closing_entry_model',
    #         'closing_entry_model__entity_model'
    #     )

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
    tx_type = models.CharField(choices=TransactionModel.TX_TYPE,
                               max_length=10,
                               verbose_name=_('Transaction Type'))
    balance = models.DecimalField(verbose_name=_('Closing Entry Balance'),
                                  max_digits=20,
                                  decimal_places=6,
                                  validators=[MinValueValidator(limit_value=Decimal('0.00'))])

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

    def is_debit(self) -> Optional[bool]:
        if self.tx_type is not None:
            return self.tx_type == TransactionModel.DEBIT

    def is_credit(self) -> Optional[bool]:
        if self.tx_type is not None:
            return self.tx_type == TransactionModel.CREDIT

    def adjust_tx_type_for_negative_balance(self):
        if self.balance < Decimal('0.00'):
            if self.is_credit():
                self.tx_type = TransactionModel.DEBIT
            elif self.is_debit():
                self.tx_type = TransactionModel.CREDIT
            self.balance = abs(self.balance)

    def get_html_id(self) -> str:
        return f'closing-entry-txs-{self.uuid}'

    def clean(self):
        self.adjust_tx_type_for_negative_balance()


class ClosingEntryTransactionModel(ClosingEntryTransactionModelAbstract):
    """
    Base ClosingEntryModel Class
    """


def closingentrymodel_presave(instance: ClosingEntryModel, **kwargs):
    instance.create_entry_ledger(commit=False)


pre_save.connect(closingentrymodel_presave, sender=ClosingEntryModel)


def closingentrytransactionmodel_presave(instance: ClosingEntryTransactionModel, **kwargs):
    instance.adjust_tx_type_for_negative_balance()


pre_save.connect(closingentrytransactionmodel_presave, sender=ClosingEntryTransactionModel)
