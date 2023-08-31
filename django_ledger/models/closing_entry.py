from typing import Optional
from uuid import uuid4, UUID

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.models import lazy_loader
from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.mixins import CreateUpdateMixIn, MarkdownNotesMixIn


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

    # ACTIONS POST...
    def can_post(self) -> bool:
        return not self.is_posted()

    def mark_as_posted(self, commit: bool = False, **kwargs):
        if not self.can_post():
            raise ClosingEntryValidationError(
                message=_(f'Closing Entry {self.closing_date} is already posted.')
            )
        self.posted = True
        if commit:
            self.save(update_fields=[
                'posted',
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
        if commit:
            self.save(update_fields=[
                'posted',
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
        return super().delete(**kwargs)

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

    def get_html_id(self) -> str:
        return f'closing-entry-txs-{self.uuid}'


class ClosingEntryTransactionModel(ClosingEntryTransactionModelAbstract):
    """
    Base ClosingEntryModel Class
    """
