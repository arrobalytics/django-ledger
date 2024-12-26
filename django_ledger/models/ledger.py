"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

The LedgerModel is the heart of Django Ledger. It is a self-contained unit of accounting that implements a
double-entry accounting system capable of creating and managing transactions into the ledger and producing any financial
statements. In essence, an EntityModel is made of a collection of LedgerModels that drive the whole bookkeeping process.
Each LedgerModel is independent and they can operate as an individual or as a group.

Each LedgerModel encapsulates a collection of JournalEntryModels, which in turn hold a collection of TransactionModels.
LedgerModels can be used to represent any part of the EntityModel and can be extended to add additional functionality
and custom logic that drives how transactions are recorded into the books. One example of this is the LedgerWrapperMixIn
(see django_ledger.models.mixins.LedgerWrapperMixIn), which is the foundation of LedgerModel abstractions such as the
BillModel, InvoiceModel, PurchaseOrderModel and EstimateModel. Extending the LedgerModel can add additional
functionality necessary to implement industry-specific functionality to almost anything you can think of. Examples:
Farming Equipment, Real Estate, Investment Portfolio, etc.

Also, the LedgerModel inherits functionality from the all mighty IOMixIn (see django_ledger.io.io_mixin.IOMixIn),
which is the class responsible for making accounting queries to the Database in an efficient and performing way.
The digest() method executes all necessary aggregations and optimizations in order to push as much work to the Database
layer as possible in order to minimize the amount of data being pulled for analysis into the Python memory.

The Django Ledger core model follows the following structure:
EntityModel -< LedgerModel -< JournalEntryModel -< TransactionModel
"""
from datetime import date
from string import ascii_lowercase, digits
from typing import Optional
from uuid import uuid4

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Q, Min, F, Count
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.io.io_core import IOMixIn
from django_ledger.models import lazy_loader
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.signals import (
    ledger_posted,
    ledger_unposted,
    ledger_locked,
    ledger_unlocked,
    ledger_hidden,
    ledger_unhidden
)

LEDGER_ID_CHARS = ascii_lowercase + digits


class LedgerModelValidationError(ValidationError):
    pass


class LedgerModelQuerySet(models.QuerySet):
    """
    Custom defined LedgerModel QuerySet.
    """

    def locked(self):
        """
        Filters the QuerySet to only locked LedgerModel.

        Returns
        -------
        LedgerModelQuerySet
            A QuerySet with applied filters.
        """
        return self.filter(locked=True)

    def unlocked(self):
        """
        Filters the QuerySet to only un-locked LedgerModel.

        Returns
        -------
        LedgerModelQuerySet
            A QuerySet with applied filters.
        """
        return self.filter(locked=False)

    def posted(self):
        """
        Filters the QuerySet to only posted LedgerModel.

        Returns
        -------
        LedgerModelQuerySet
            A QuerySet with applied filters.
        """
        return self.filter(posted=True)

    def unposted(self):
        """
        Filters the QuerySet to only un-posted LedgerModel.

        Returns
        -------
        LedgerModelQuerySet
            A QuerySet with applied filters.
        """
        return self.filter(posted=True)

    def hidden(self):
        return self.filter(hidden=True)

    def visible(self):
        return self.filter(hidden=False)

    def current(self):
        return self.filter(
            Q(earliest_timestamp__date__gt=F('entity__last_closing_date'))
            | Q(earliest_timestamp__isnull=True)
        )


class LedgerModelManager(models.Manager):
    """
    A custom-defined LedgerModelManager that implements custom QuerySet methods related to the LedgerModel.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('entity').annotate(
            Count('journal_entries'),
            earliest_timestamp=Min('journal_entries__timestamp',
                                   filter=Q(journal_entries__posted=True)),
        )

    def for_user(self, user_model):
        qs = self.get_queryset()
        if user_model.is_superuser:
            return qs
        return qs.filter(
            Q(entity__admin=user_model) |
            Q(entity__managers__in=[user_model])
        )

    def for_entity(self, entity_slug, user_model):
        """
        Returns a QuerySet of LedgerModels associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        ----------
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model
            The request UserModel to check for privileges.

        Returns
        -------
        LedgerModelQuerySet
            A Filtered LedgerModelQuerySet.
        """
        qs = self.for_user(user_model)
        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return qs.filter(
                Q(entity=entity_slug)
            )
        return qs.filter(
            Q(entity__slug__exact=entity_slug)
        )


class LedgerModelAbstract(CreateUpdateMixIn, IOMixIn):
    """
    Base implmentation of the LedgerModel.

    Attributes
    ----------
    uuid: UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().
    name: str
        Human-readable name of the LedgerModel. Maximum 150 characters.
    ledger_xid: str
        A unique user-defined identifier for the LedgerModel. Unique for the Entity Model.
    entity: EntityModel
        The EntityModel associated with the LedgerModel instance.
    posted: bool
        Determines if the LedgerModel is posted. Defaults to False. Mandatory.
    locked: bool
        Determines if the LedgerModel is locked. Defaults to False. Mandatory.
    hidden: bool
        Determines if the LedgerModel is hidden. Defaults to False. Mandatory.
    """
    _WRAPPED_MODEL_KEY = 'wrapped_model'
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    ledger_xid = models.SlugField(allow_unicode=True, max_length=150, null=True, blank=True,
                                  verbose_name=_('Ledger External ID'),
                                  help_text=_('User Defined Ledger ID'))
    name = models.CharField(max_length=150, null=True, blank=True, verbose_name=_('Ledger Name'))

    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Ledger Entity'))
    posted = models.BooleanField(default=False, verbose_name=_('Posted Ledger'))
    locked = models.BooleanField(default=False, verbose_name=_('Locked Ledger'))
    hidden = models.BooleanField(default=False, verbose_name=_('Hidden Ledger'))
    additional_info = models.JSONField(default=dict,
                                       encoder=DjangoJSONEncoder,
                                       null=True,
                                       blank=True)

    objects = LedgerModelManager.from_queryset(queryset_class=LedgerModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Ledger')
        verbose_name_plural = _('Ledgers')
        indexes = [
            models.Index(fields=['entity']),
            models.Index(fields=['entity', 'posted']),
            models.Index(fields=['entity', 'locked']),
            models.Index(fields=['entity', 'ledger_xid']),
            models.Index(fields=['ledger_xid']),
        ]
        unique_together = [
            ('entity', 'ledger_xid')
        ]

    def __str__(self):
        if self.name is not None:
            ledger_str = f'LedgerModel: {self.name}'
        elif self.ledger_xid is not None:
            ledger_str = f'LedgerModel: {self.ledger_xid}'
        else:
            ledger_str = f'LedgerModel: {self.uuid}'
        return f'{ledger_str} | Posted: {self.posted} | Locked: {self.locked}'

    def has_wrapped_model_info(self):
        if self.additional_info is not None:
            return self._WRAPPED_MODEL_KEY in self.additional_info
        return False

    def has_wrapped_model(self):
        if self.has_wrapped_model_info():
            return True

        wrapped_model_info = self.get_wrapper_info
        for model_class, model_id in wrapped_model_info.items():
            try:
                return getattr(self, model_id)
            except ObjectDoesNotExist:
                pass
        return False

    def remove_wrapped_model_info(self):
        if self.has_wrapped_model_info():
            del self.additional_info[self._WRAPPED_MODEL_KEY]

    def has_jes_in_locked_period(self, force_evaluation: bool = True) -> bool:
        try:
            earliest_posted_je_timestamp = getattr(self, 'earliest_timestamp')
        except AttributeError:
            if force_evaluation:
                try:
                    earliest_je = self.journal_entries.posted().order_by('-timestamp').only('timestamp').first()
                    self.earliest_timestamp = earliest_je.timestamp if earliest_je else None
                except ObjectDoesNotExist:
                    self.earliest_timestamp = None
                earliest_posted_je_timestamp = getattr(self, 'earliest_timestamp')
            else:
                raise LedgerModelValidationError(
                    message=_(f'earliest_timestamp not present in LedgerModel {self.uuid}'))

        last_closing_date = self.get_entity_last_closing_date()
        if last_closing_date is None:
            return False
        if earliest_posted_je_timestamp is not None:
            earliest_posted_je_date = earliest_posted_je_timestamp.date()
            return earliest_posted_je_date <= last_closing_date
        return False

    def configure_for_wrapper_model(self, model_instance, commit: bool = False):

        if self.additional_info is None:
            self.additional_info = dict()

        wrapper_info = self.get_wrapper_info
        self.additional_info[self._WRAPPED_MODEL_KEY] = {
            'model': wrapper_info[model_instance.__class__],
            'uuid': model_instance.uuid
        }

        if commit:
            self.save(update_fields=[
                'additional_info',
                'updated'
            ])

    @property
    def get_wrapper_info(self):
        return {
            lazy_loader.get_bill_model(): 'billmodel',
            lazy_loader.get_invoice_model(): 'invoicemodel',
        }

    def get_wrapped_model_instance(self):
        if self.has_wrapped_model_info():
            return getattr(self, self.additional_info[self._WRAPPED_MODEL_KEY]['model'])

        for model_class, attr in self.get_wrapper_info.items():
            if getattr(self, attr, None):
                return getattr(self, attr)

    def get_wrapped_model_url(self):
        if self.has_wrapped_model():
            wrapped_model = self.get_wrapped_model_instance()
            return wrapped_model.get_absolute_url()

    def is_posted(self) -> bool:
        """
        Determines if the LedgerModel instance is posted.

        Returns
        -------
        bool
            True if posted, else False.
        """
        return self.posted is True

    def is_locked(self) -> bool:
        """
        Determines if the LedgerModel instance is locked.

        Returns
        -------
        bool
            True if locked, else False.
        """
        return self.locked is True

    def is_hidden(self) -> bool:
        """
        Determines if the LedgerModel instance is hidden.

        Returns
        -------
        bool
            True if hidden, else False.
        """
        return self.hidden is True

    def can_post(self) -> bool:
        """
        Determines if the LedgerModel can be marked as posted.

        Returns
        -------
        bool
            True if can be posted, else False.
        """
        return all([
            not self.is_posted(),
            not self.is_locked(),
            not self.has_jes_in_locked_period()
        ])

    def can_unpost(self) -> bool:
        """
        Determines if the LedgerModel can be un-posted.

        Returns
        -------
        bool
            True if can be un-posted, else False.
        """
        return all([
            self.is_posted(),
            not self.is_locked(),
            not self.has_jes_in_locked_period()
        ])

    def can_lock(self) -> bool:
        """
        Determines if the LedgerModel can be locked.

        Returns
        -------
        bool
            True if can be locked, else False.
        """
        return all([
            not self.is_locked(),
            self.is_posted()
        ])

    def can_unlock(self) -> bool:
        """
        Determines if the LedgerModel can be un-locked.

        Returns
        -------
        bool
            True if can be un-locked, else False.
        """
        return all([
            self.is_locked(),
            self.is_posted()
        ])

    def can_hide(self) -> bool:
        """
        Determines if the LedgerModel can be hidden.

        Returns
        -------
        bool
            True if can be hidden, else False.
        """
        return self.hidden is False

    def can_unhide(self) -> bool:
        """
        Determines if the LedgerModel can be un-hidden.

        Returns
        -------
        bool
            True if can be un-hidden, else False.
        """
        return self.hidden is True

    def can_delete(self) -> bool:
        if all([
            not self.is_locked(),
            not self.is_posted(),
            not self.has_wrapped_model_info(),
            not self.has_jes_in_locked_period()
        ]):
            return True
        return False

    def can_edit_journal_entries(self) -> bool:
        return not self.is_locked()

    def post(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        """
        Posts the LedgerModel.

        Parameters
        ----------
        commit: bool
            If True, saves the LedgerModel instance instantly. Defaults to False.
        raise_exception:bool
            Raises LedgerModelValidationError if posting not allowed.
        """
        if not self.can_post():
            if raise_exception:
                raise LedgerModelValidationError(
                    message=_(f'Ledger {self.name} cannot be posted. UUID: {self.uuid}')
                )
            return
        self.posted = True
        if commit:
            self.save(update_fields=[
                'posted',
                'updated'
            ])
        ledger_posted.send_robust(sender=self.__class__,
                                  instance=self,
                                  commited=commit,
                                  **kwargs)

    def post_journal_entries(self, commit: bool = True, **kwargs):
        je_model_qs = self.journal_entries.unposted()
        for je_model in je_model_qs:
            je_model.mark_as_posted(raise_exception=False, commit=False)
        if commit:
            je_model_qs.bulk_update(objs=je_model_qs, fields=['posted', 'updated'])
        return je_model_qs

    def unpost(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        """
        Un-posts the LedgerModel.

        Parameters
        ----------
        commit: bool
            If True, saves the LedgerModel instance instantly. Defaults to False.
        raise_exception:bool
            Raises LedgerModelValidationError if un-posting not allowed.
        """
        if not self.can_unpost():
            if raise_exception:
                raise LedgerModelValidationError(
                    message=_(f'Ledger {self.uuid} cannot be unposted.')
                )
            return
        self.posted = False
        if commit:
            self.save(update_fields=[
                'posted',
                'updated'
            ])
        ledger_unposted.send_robust(sender=self.__class__,
                                    instance=self,
                                    commited=commit,
                                    **kwargs)

    def lock(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        """
        Locks the LedgerModel.

        Parameters
        ----------
        commit: bool
            If True, saves the LedgerModel instance instantly. Defaults to False.
        raise_exception: bool
            Raises LedgerModelValidationError if locking not allowed.
        """

        if not self.can_lock():
            if raise_exception:
                raise LedgerModelValidationError(
                    message=_(f'Ledger {self.name} cannot be locked. UUID: {self.uuid}')
                )
            return
        self.locked = True
        if commit:
            self.save(update_fields=[
                'locked',
                'updated'
            ])
        ledger_locked.send_robust(sender=self.__class__,
                                  instance=self,
                                  commited=commit,
                                  **kwargs)

    def lock_journal_entries(self, commit: bool = True, **kwargs):
        je_model_qs = self.journal_entries.unlocked()
        for je_model in je_model_qs:
            je_model.mark_as_locked(raise_exception=False, commit=False)
        if commit:
            je_model_qs.bulk_update(objs=je_model_qs, fields=['locked', 'updated'])
        return je_model_qs

    def unlock(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        """
        Un-locks the LedgerModel.

        Parameters
        ----------
        commit: bool
            If True, saves the LedgerModel instance instantly. Defaults to False.
        """
        if not self.can_unlock():
            if raise_exception:
                raise LedgerModelValidationError(
                    message=_(f'Ledger {self.name} cannot be un-locked. UUID: {self.uuid}')
                )
            return

        self.locked = False
        if commit:
            self.save(update_fields=[
                'locked',
                'updated'
            ])
        ledger_unlocked.send_robust(sender=self.__class__,
                                    instance=self,
                                    commited=commit,
                                    **kwargs)

    def hide(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        if not self.can_hide():
            if raise_exception:
                raise LedgerModelValidationError(
                    message=_(f'Ledger {self.name} cannot be hidden. UUID: {self.uuid}')
                )
            return
        self.hidden = True
        if commit:
            self.save(update_fields=[
                'hidden',
                'updated'
            ])
        ledger_hidden.send_robust(sender=self.__class__,
                                  instance=self,
                                  commited=commit,
                                  **kwargs)

    def unhide(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        if not self.can_unhide():
            if raise_exception:
                raise LedgerModelValidationError(
                    message=_(f'Ledger {self.name} cannot be un-hidden. UUID: {self.uuid}')
                )
            return
        self.hidden = False
        if commit:
            self.save(update_fields=[
                'hidden',
                'updated'
            ])
        ledger_unhidden.send_robust(sender=self.__class__,
                                    instance=self,
                                    commited=commit,
                                    **kwargs)

    def delete(self, **kwargs):
        if not self.can_delete():
            raise LedgerModelValidationError(
                message=_(f'LedgerModel {self.name} cannot be deleted because posted is {self.is_posted()} '
                          f'and locked is {self.is_locked()}')
            )

        # checks if ledger model has journal entries in a closed period...
        if self.entity.has_closing_entry():
            earliest_je_timestamp = self.journal_entries.posted().order_by('-timestamp').values('timestamp').first()
            if earliest_je_timestamp is not None:
                earliest_date = earliest_je_timestamp['timestamp'].date()
                if earliest_date <= self.entity.last_closing_date:
                    raise LedgerModelValidationError(
                        message=_(
                            f'Journal Entries with date {earliest_date} cannot be deleted because of latest closing '
                            f'entry on {self.get_entity_last_closing_date()}')
                    )
        return super().delete(**kwargs)

    def get_entity_name(self) -> str:
        return self.entity.name

    def get_entity_last_closing_date(self) -> Optional[date]:
        return self.entity.last_closing_date

    def get_absolute_url(self) -> str:
        """
        Determines the absolute URL of the LedgerModel instance.
        Results in additional Database query if entity field is not selected in QuerySet.

        Returns
        -------
        str
            URL as a string.
        """
        return reverse(viewname='django_ledger:je-list',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ledger_pk': self.uuid
                       })

    def get_create_url(self) -> str:
        """
        Determines the update URL of the LedgerModel instance.
        Results in additional Database query if entity field is not selected in QuerySet.

        Returns
        -------
        str
            URL as a string.
        """
        return reverse('django_ledger:ledger-create',
                       kwargs={
                           'entity_slug': self.entity.slug
                       })

    def get_update_url(self) -> str:
        """
        Determines the update URL of the LedgerModel instance.
        Results in additional Database query if entity field is not selected in QuerySet.

        Returns
        -------
        str
            URL as a string.
        """
        return reverse('django_ledger:ledger-update',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ledger_pk': self.uuid
                       })

    def get_list_url(self) -> str:
        """
        Determines the list URL of the LedgerModel instances.
        Results in additional Database query if entity field is not selected in QuerySet.

        Returns
        -------
        str
            URL as a string.
        """
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.entity.slug
                       })

    def get_balance_sheet_url(self):
        return reverse(
            viewname='django_ledger:ledger-bs',
            kwargs={
                'entity_slug': self.entity.slug,
                'ledger_pk': self.uuid
            }
        )

    def get_income_statement_url(self):
        return reverse(
            viewname='django_ledger:ledger-ic',
            kwargs={
                'entity_slug': self.entity.slug,
                'ledger_pk': self.uuid
            }
        )

    def get_cash_flow_statement_url(self):
        return reverse(
            viewname='django_ledger:ledger-cf',
            kwargs={
                'entity_slug': self.entity.slug,
                'ledger_pk': self.uuid
            }
        )

    def get_delete_message(self):
        return _(f'Are you sure you want to delete Ledger {self.name} from Entity {self.get_entity_name()}?')


class LedgerModel(LedgerModelAbstract):
    """
    Base LedgerModel from Abstract.
    """
    class Meta(LedgerModelAbstract.Meta):
        swappable = 'DJANGO_LEDGER_LEDGER_MODEL'
        abstract = False


def ledgermodel_presave(instance: LedgerModel, **kwargs):
    if not instance.has_wrapped_model_info():
        wrapper_instance = instance.get_wrapped_model_instance()
        instance.configure_for_wrapper_model(model_instance=wrapper_instance)
