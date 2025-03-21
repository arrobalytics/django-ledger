"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

A Journal Entry (JE) is the foundation of all double entry accounting and financial data of any EntityModel.
A JE encapsulates a collection of TransactionModel, which must contain two transactions at a minimum. Each transaction
must perform a DEBIT or a CREDIT to an AccountModel. The JE Model performs additional validation to make sure that
the sum of all DEBITs and the sum of all CREDITs are equal to keep the books balanced.

A JE by default will be un-posted, which means that simply creating a JE will have no effect on the EntityModel
books. This behavior allows for constant refinement and persistence of JEs in the database without any impact on the
books. Only Journal Entries contained within a *POSTED* LedgerModel (see LedgerModel for documentation) will have an
impact in the EntityModel finances.

The JournalEntryModel also carries an optional EntityUnitModel, which are logical user-defined labels which help
segregate the different financial statements into different business operations (see EntityUnitModel for documentation).
Examples of EntityModelUnits are offices, departments, divisions, etc. *The user may request financial statements by
unit*.

All JEs automatically generate a sequential Journal Entry Number, which takes into consideration the Fiscal Year of the
JournalEntryModel instance. This functionality enables a human-readable tracking mechanism which helps with audits. It
is also searchable and indexed to support quick searches and queries.

The JournalEntryModel is also responsible for validating the Financial Activity involved in the operations of the
business. Whenever an account with ASSET_CA_CASH role is involved in a Journal Entry (see roles for more details), the
JE is responsible for programmatically determine the kind of operation for the JE (Operating, Financing, Investing).
"""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from itertools import chain
from typing import Set, Union, Optional, Dict, Tuple, List
from uuid import uuid4, UUID

from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Sum, QuerySet, F, Manager, Count
from django.db.models.functions import Coalesce
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from django_ledger.io.io_core import get_localtime
from django_ledger.io.roles import (
    ASSET_CA_CASH, GROUP_CFS_FIN_DIVIDENDS, GROUP_CFS_FIN_ISSUING_EQUITY,
    GROUP_CFS_FIN_LT_DEBT_PAYMENTS, GROUP_CFS_FIN_ST_DEBT_PAYMENTS,
    GROUP_CFS_INVESTING_AND_FINANCING, GROUP_CFS_INVESTING_PPE,
    GROUP_CFS_INVESTING_SECURITIES,
    validate_roles
)
from django_ledger.models.accounts import CREDIT, DEBIT
from django_ledger.models.entity import EntityStateModel, EntityModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.signals import (
    journal_entry_unlocked,
    journal_entry_locked,
    journal_entry_posted,
    journal_entry_unposted
)
from django_ledger.models.transactions import TransactionModelQuerySet, TransactionModel
from django_ledger.settings import (
    DJANGO_LEDGER_JE_NUMBER_PREFIX,
    DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
    DJANGO_LEDGER_JE_NUMBER_NO_UNIT_PREFIX
)
from django_ledger.io import roles


class JournalEntryValidationError(ValidationError):
    pass


class JournalEntryModelQuerySet(QuerySet):
    """
    A custom QuerySet for working with Journal Entry models, providing additional
    convenience methods and validations for specific use cases.

    This class enhances Django's default QuerySet by adding tailored methods
    to manage and filter Journal Entries, such as handling posted, unposted,
    locked entries, and querying entries associated with specific ledgers.
    """

    def create(self, verify_on_save: bool = False, force_create: bool = False, **kwargs):
        """
        Creates a new Journal Entry while enforcing business logic validations.

        This method overrides Django's default `create()` to ensure that Journal Entries
        cannot be created in a "posted" state unless explicitly overridden.
        Additionally, it offers optional pre-save verification.

        Parameters
        ----------
        verify_on_save : bool
            If True, performs a verification step before saving. This avoids
            additional database queries for validation when creating new entries.
            Should be used when the Journal Entry needs no transactional validation.
        force_create : bool
            If True, allows the creation of a Journal Entry even in a "posted"
            state. Use with caution and only if you are certain of the consequences.
        **kwargs : dict
            Additional keyword arguments passed to instantiate the Journal Entry model.

        Returns
        -------
        JournalEntryModel
            The newly created Journal Entry.

        Raises
        ------
        FieldError
            Raised if attempting to create a "posted" Journal Entry without
            setting `force_create=True`.
        """
        is_posted = kwargs.get('posted')
        if is_posted and not force_create:
            raise FieldError("Cannot create Journal Entries in a posted state without 'force_create=True'.")

        obj = self.model(**kwargs)
        self._for_write = True

        # Save the object with optional pre-save verification.
        obj.save(force_insert=True, using=self.db, verify=verify_on_save)
        return obj

    def posted(self):
        """
        Filters the QuerySet to include only "posted" Journal Entries.

        Returns
        -------
        JournalEntryModelQuerySet
            A filtered QuerySet containing only posted Journal Entries.
        """
        return self.filter(posted=True)

    def unposted(self):
        """
        Filters the QuerySet to include only "unposted" Journal Entries.

        Returns
        -------
        JournalEntryModelQuerySet
            A filtered QuerySet containing only unposted Journal Entries.
        """
        return self.filter(posted=False)

    def locked(self):
        """
        Filters the QuerySet to include only "locked" Journal Entries.

        Returns
        -------
        JournalEntryModelQuerySet
            A filtered QuerySet containing only locked Journal Entries.
        """
        return self.filter(locked=True)

    def unlocked(self):
        """
        Filters the QuerySet to include only "unlocked" Journal Entries.

        Returns
        -------
        JournalEntryModelQuerySet
            A filtered QuerySet containing only unlocked Journal Entries.
        """
        return self.filter(locked=False)

    def for_ledger(self, ledger_pk: Union[str, UUID, LedgerModel]):
        """
        Filters the QuerySet to include Journal Entries associated with a specific Ledger.

        Parameters
        ----------
        ledger_pk : str, UUID, or LedgerModel
            The LedgerModel instance, its UUID, or a string representation of the UUID
            to identify the Ledger.

        Returns
        -------
        JournalEntryModelQuerySet
            A filtered QuerySet of Journal Entries associated with the specified Ledger.
        """
        if isinstance(ledger_pk, LedgerModel):
            return self.filter(ledger=ledger_pk)
        return self.filter(ledger__uuid__exact=ledger_pk)


class JournalEntryModelManager(Manager):
    """
    A custom manager for the JournalEntryModel that extends Django's default
    Manager with additional query features. It allows complex query handling
    based on relationships to the `EntityModel` and the authenticated `UserModel`.

    This manager provides utility methods for generating filtered querysets
    (e.g., entries associated with specific users or entities), as well as
    annotations for convenience in query results.
    """

    def get_queryset(self) -> JournalEntryModelQuerySet:
        """
        Returns the default queryset for JournalEntryModel with additional
        annotations applied.

        Annotations:
        - `_entity_slug`: The slug of the related `EntityModel`.
        - `txs_count`: The count of transactions (related `TransactionModel` instances)
          for each journal entry.

        Returns
        -------
        JournalEntryModelQuerySet
            A custom queryset enhanced with annotations.
        """
        qs = JournalEntryModelQuerySet(self.model, using=self._db)
        return qs.annotate(
            _entity_uuid=F('ledger__entity_id'),
            _entity_slug=F('ledger__entity__slug'),  # Annotates the entity slug
            _entity_last_closing_date=F('ledger__entity__last_closing_date'),
            _ledger_is_locked=F('ledger__locked'),
            txs_count=Count('transactionmodel')  # Annotates the count of transactions
        )

    def for_user(self, user_model) -> JournalEntryModelQuerySet:
        """
        Filters the JournalEntryModel queryset for the given user.

        - Superusers will have access to all journal entries.
        - Other authenticated users will only see entries for entities where
          they are admins or managers.

        Parameters
        ----------
        user_model : UserModel
            An authenticated Django user object.

        Returns
        -------
        JournalEntryModelQuerySet
            A filtered queryset restricted by the user's entity relationships.
        """
        qs = self.get_queryset()
        if user_model.is_superuser:
            return qs

        return qs.filter(
            Q(ledger__entity__admin=user_model) |  # Entries for entities where the user is admin
            Q(ledger__entity__managers__in=[user_model])  # Entries for entities where the user is a manager
        )

    def for_entity(self, entity_slug: Union[str, EntityModel], user_model) -> JournalEntryModelQuerySet:
        """
        Filters the JournalEntryModel queryset for a specific entity and user.

        This method provides a way to fetch journal entries related to a specific
        `EntityModel`, identified by its slug or model instance, with additional
        filtering scoped to the user.

        Parameters
        ----------
        entity_slug : str or EntityModel
            The slug of the entity (or an instance of `EntityModel`) used for filtering.
        user_model : UserModel
            An authenticated Django user object.

        Returns
        -------
        JournalEntryModelQuerySet
            A customized queryset containing journal entries associated with the
            given entity and restricted by the user's access permissions.
        """
        qs = self.for_user(user_model)

        # Handle the `entity_slug` as either a string or an EntityModel instance
        if isinstance(entity_slug, EntityModel):
            return qs.filter(ledger__entity=entity_slug)

        return qs.filter(ledger__entity__slug__iexact=entity_slug)  # Case-insensitive slug match


class ActivityEnum(Enum):
    """
    Represents the database prefixes used for different types of accounting activities.

    Attributes
    ----------
    OPERATING : str
        Prefix for a Journal Entry categorized as an Operating Activity.
    INVESTING : str
        Prefix for a Journal Entry categorized as an Investing Activity.
    FINANCING : str
        Prefix for a Journal Entry categorized as a Financing Activity.
    """
    OPERATING = 'op'
    INVESTING = 'inv'
    FINANCING = 'fin'


class JournalEntryModelAbstract(CreateUpdateMixIn):
    """
    Abstract base model for handling journal entries in the bookkeeping system.

    Attributes
    ----------
    uuid : UUID
        A unique identifier (primary key) for the journal entry, generated using uuid4().
    je_number : str
        A human-readable, unique, alphanumeric identifier for the journal entry (e.g., Voucher or Document Number).
        Includes the fiscal year as a prefix for organizational purposes.
    timestamp : datetime
        The date of the journal entry, used for financial statements. This timestamp applies to associated transactions.
    description : str
        An optional user-defined description for the journal entry.
    entity_unit : EntityUnitModel
        A reference to a logical and self-contained structure within the `EntityModel`.
        Provides context for the journal entry. See `EntityUnitModel` documentation for details.
    activity : str
        Indicates the nature of the activity associated with the journal entry.
        Must be one of the predefined `ACTIVITIES` (e.g., Operating, Financing, Investing) and is programmatically determined.
    origin : str
        Describes the origin or trigger for the journal entry (e.g., reconciliations, migrations, auto-generated).
        Max length: 30 characters.
    posted : bool
        Determines whether the journal entry has been posted (affecting the books). Defaults to `False`.
    locked : bool
        Indicates whether the journal entry is locked, preventing further modifications. Defaults to `False`.
    ledger : LedgerModel
        A reference to the LedgerModel associated with this journal entry. This field is mandatory.
    is_closing_entry : bool
        Indicates if the journal entry is a closing entry. Defaults to `False`.
    """

    # Constants for activity types
    OPERATING_ACTIVITY = ActivityEnum.OPERATING.value
    FINANCING_OTHER = ActivityEnum.FINANCING.value
    INVESTING_OTHER = ActivityEnum.INVESTING.value
    INVESTING_SECURITIES = f'{ActivityEnum.INVESTING.value}_securities'
    INVESTING_PPE = f'{ActivityEnum.INVESTING.value}_ppe'
    FINANCING_STD = f'{ActivityEnum.FINANCING.value}_std'
    FINANCING_LTD = f'{ActivityEnum.FINANCING.value}_ltd'
    FINANCING_EQUITY = f'{ActivityEnum.FINANCING.value}_equity'
    FINANCING_DIVIDENDS = f'{ActivityEnum.FINANCING.value}_dividends'

    # Activity categories for dropdown
    ACTIVITIES = [
        (_('Operating'), (
            (OPERATING_ACTIVITY, _('Operating')),
        )),
        (_('Investing'), (
            (INVESTING_PPE, _('Purchase/Disposition of PPE')),
            (INVESTING_SECURITIES, _('Purchase/Disposition of Securities')),
            (INVESTING_OTHER, _('Investing Activity Other')),
        )),
        (_('Financing'), (
            (FINANCING_STD, _('Payoff of Short Term Debt')),
            (FINANCING_LTD, _('Payoff of Long Term Debt')),
            (FINANCING_EQUITY, _('Issuance of Common Stock, Preferred Stock or Capital Contribution')),
            (FINANCING_DIVIDENDS, _('Dividends or Distributions to Shareholders')),
            (FINANCING_OTHER, _('Financing Activity Other')),
        )),
    ]

    # Utility mappings for activity validation
    VALID_ACTIVITIES = list(chain.from_iterable([[a[0] for a in cat[1]] for cat in ACTIVITIES]))
    MAP_ACTIVITIES = dict(chain.from_iterable([[(a[0], cat[0]) for a in cat[1]] for cat in ACTIVITIES]))
    NON_OPERATIONAL_ACTIVITIES = [a for a in VALID_ACTIVITIES if ActivityEnum.OPERATING.value not in a]

    # Field definitions
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    je_number = models.SlugField(max_length=25, editable=False, verbose_name=_('Journal Entry Number'))
    timestamp = models.DateTimeField(verbose_name=_('Timestamp'), default=localtime)
    description = models.CharField(max_length=70, blank=True, null=True, verbose_name=_('Description'))
    entity_unit = models.ForeignKey(
        'django_ledger.EntityUnitModel',
        on_delete=models.RESTRICT,
        blank=True,
        null=True,
        verbose_name=_('Associated Entity Unit')
    )
    activity = models.CharField(
        choices=ACTIVITIES,
        max_length=20,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_('Activity')
    )
    origin = models.CharField(max_length=30, blank=True, null=True, verbose_name=_('Origin'))
    posted = models.BooleanField(default=False, verbose_name=_('Posted'))
    locked = models.BooleanField(default=False, verbose_name=_('Locked'))
    is_closing_entry = models.BooleanField(default=False)
    ledger = models.ForeignKey(
        'django_ledger.LedgerModel',
        verbose_name=_('Ledger'),
        related_name='journal_entries',
        on_delete=models.CASCADE
    )

    # Custom manager
    objects = JournalEntryModelManager.from_queryset(queryset_class=JournalEntryModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Journal Entry')
        verbose_name_plural = _('Journal Entries')
        indexes = [
            models.Index(fields=['ledger']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['activity']),
            models.Index(fields=['entity_unit']),
            models.Index(fields=['locked']),
            models.Index(fields=['posted']),
            models.Index(fields=['je_number']),
            models.Index(fields=['is_closing_entry']),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._verified = False

    def __str__(self):
        if self.je_number:
            return f"JE: {self.je_number} (posted={self.posted}, locked={self.locked}) - Desc: {self.description or ''}"
        return f"JE ID: {self.pk} (posted={self.posted}, locked={self.locked}) - Desc: {self.description or ''}"

    @property
    def entity_uuid(self):
        try:
            return getattr(self, '_entity_uuid')
        except AttributeError:
            pass
        return self.ledger.entity_id

    @property
    def entity_slug(self):
        """
        Retrieves the unique slug associated with the entity.

        The property first attempts to return the value stored in the `_entity_slug`
        attribute if it exists. If `_entity_slug` is not set, it falls back to the
        `ledger.entity.slug` attribute.

        Returns:
            str: The slug value from `_entity_slug` if available, or `ledger.entity.slug` otherwise.
        """
        try:
            return getattr(self, '_entity_slug')
        except AttributeError:
            pass
        return self.ledger.entity.slug

    @property
    def entity_model(self) -> EntityModel:
        """
        Provides access to the `EntityModel` related to the JournalEntryModel.

        Returns
        -------
        EntityModel
            The `EntityModel` instance linked to the instance LedgerModel.
        """
        return self.ledger.entity

    @property
    def entity_last_closing_date(self) -> Optional[date]:
        """
            Retrieves the last closing date for an entity, if available.

            This property returns the date of the most recent closing event
            associated with the entity. If no closing date exists, the
            result will be None.

            Returns
            -------
            Optional[date]
                The date of the last closing event, or None if no closing
                date is available.
        """
        return self.get_entity_last_closing_date()

    def validate_for_entity(self, entity_model: Union[EntityModel, str, UUID], raise_exception: bool = True) -> bool:
        """
        Validates whether the given entity_model owns thr Journal Entry instance.

        This method checks if the provided entity_model owns the Journal Entry model instance.
        The entity_model can be of type `EntityModel`, `str`, or
        `UUID`. The method performs type-specific checks to ensure proper validation
        and returns the validation result.

        Parameters
        ----------
        entity_model : Union[EntityModel, str, UUID]
            The entity to validate against. It can either be an instance of the
            `EntityModel`, a string representation of a UUID, or a UUID object.

        Returns
        -------
        bool
            A boolean value. True if the given entity_model corresponds to the current
            entity's UUID, otherwise False.
        """
        if isinstance(entity_model, str):
            is_valid = str(self.entity_uuid) == entity_model
        elif isinstance(entity_model, UUID):
            is_valid = self.entity_uuid == entity_model
        else:
            is_valid = self.entity_uuid == entity_model.uuid

        if not is_valid and raise_exception:
            raise JournalEntryValidationError(
                message='The Journal Entry does not belong to the provided entity.'
            )
        return is_valid

    def ledger_is_locked(self):
        """
        Determines whether the ledger is locked.

        This method checks the current state of the ledger to determine if it is
        locked and unavailable for further operations. It looks for an annotated
        attribute `_ledger_is_locked` and returns its value if found. If the
        attribute is not set, it delegates the check to the actual `is_locked`
        method of the `ledger` object.

        Returns
        -------
        bool
            A boolean value indicating whether the ledger is locked.
        """
        try:
            return getattr(self, '_ledger_is_locked')
        except AttributeError:
            pass
        return self.ledger.is_locked()

    def can_post(self, ignore_verify: bool = True) -> bool:
        """Determines if the journal entry can be posted."""
        return all([
            self.is_locked(),
            not self.is_posted(),
            self.is_verified() if not ignore_verify else True,  # avoids db queries, will be verified before saving
            not self.ledger_is_locked(),
            not self.is_in_locked_period()
        ])

    def can_unpost(self) -> bool:
        """Checks if the journal entry can be un-posted."""
        return all([
            self.is_posted(),
            not self.ledger_is_locked(),
            not self.is_in_locked_period()
        ])

    def can_lock(self) -> bool:
        """Determines if the journal entry can be locked."""
        return all([
            not self.is_locked(),
            not self.ledger_is_locked()
        ])

    def can_unlock(self) -> bool:
        """Checks if the journal entry can be unlocked."""
        return all([
            self.is_locked(),
            not self.is_posted(),
            not self.is_in_locked_period(),
            not self.ledger_is_locked()
        ])

    def can_delete(self) -> bool:
        """Checks if the journal entry can be deleted."""
        return all([
            not self.is_locked(),
            not self.is_posted(),
        ])

    def can_edit(self) -> bool:
        """Checks if the journal entry is editable."""
        return all([
            not self.is_locked(),

        ])

    def is_posted(self) -> bool:
        """Returns whether the journal entry has been posted."""
        return self.posted is True

    def is_in_locked_period(self, new_timestamp: Optional[Union[date, datetime]] = None) -> bool:
        """
        Checks if the current Journal Entry falls within a locked period.

        Parameters
        ----------
            new_timestamp: Optional[Union[date, datetime]])
                An optional date or timestamp to be checked instead of the current timestamp.

        Returns
        -------
            bool: True if the Journal Entry is in a locked period, otherwise False.
        """
        last_closing_date = self.entity_last_closing_date
        if last_closing_date is not None:
            if not new_timestamp:
                return last_closing_date >= self.timestamp.date()
            elif isinstance(new_timestamp, datetime):
                return last_closing_date >= new_timestamp.date()
            return last_closing_date >= new_timestamp
        return False

    def is_locked(self) -> bool:
        """
        Determines if the Journal Entry is locked.

        A Journal Entry is considered locked if it is posted, explicitly marked
        as locked, falls within a locked period, or the associated ledger is locked.

        Returns:
            bool: True if the Journal Entry is locked, otherwise False.
        """
        return self.is_posted() or any([
            self.locked,
            self.is_in_locked_period(),
            self.ledger_is_locked()
        ])

    def is_verified(self) -> bool:
        """
        Checks if the Journal Entry is verified.

        Returns:
            bool: True if the Journal Entry is verified, otherwise False.
        """
        return self._verified

    def is_balance_valid(self, txs_qs: TransactionModelQuerySet, raise_exception: bool = True) -> bool:
        """
        Validates whether the DEBITs and CREDITs of the transactions balance correctly.

        Parameters:
            txs_qs (TransactionModelQuerySet): A QuerySet containing transactions to validate.
            raise_exception (bool): Whether to raise a JournalEntryValidationError if the validation fails.

        Returns:
            bool: True if the transactions are balanced, otherwise False.

        Raises:
            JournalEntryValidationError: If the transactions are not balanced and raise_exception is True.
        """
        if len(txs_qs) > 0:
            balances = self.get_txs_balances(txs_qs=txs_qs, as_dict=True)
            is_valid = balances[CREDIT] == balances[DEBIT]
            if not is_valid:
                if raise_exception:
                    raise JournalEntryValidationError(
                        message='Balance of {0} CREDITs are {1} does not match DEBITs {2}.'.format(
                            self,
                            balances[CREDIT],
                            balances[DEBIT]
                        )
                    )
            return is_valid
        return True

    def is_txs_qs_coa_valid(self, txs_qs: TransactionModelQuerySet, raise_exception: bool = True) -> bool:
        """
        Validates that all transactions in the QuerySet are associated with the same Chart of Accounts (COA).

        Parameters:
            txs_qs (TransactionModelQuerySet): A QuerySet containing transactions to validate.

        Returns:
            bool: True if all transactions have the same Chart of Accounts, otherwise False.
        """
        if len(txs_qs) > 0:
            coa_count = len(set(tx.coa_id for tx in txs_qs))
            is_valid = coa_count == 1
            if not is_valid and raise_exception:
                raise JournalEntryValidationError(
                    message='All transactions in the QuerySet must be associated with the same Chart of Accounts.'
                )
            return is_valid
        return True

    def is_txs_qs_valid(self, txs_qs: TransactionModelQuerySet, raise_exception: bool = True) -> bool:
        """
        Validates whether the given Transaction QuerySet belongs to the current Journal Entry.

        Parameters:
            txs_qs (TransactionModelQuerySet): A QuerySet containing transactions to validate.
            raise_exception (bool): Whether to raise a JournalEntryValidationError if the validation fails.

        Returns:
            bool: True if all transactions belong to the Journal Entry, otherwise False.

        Raises:
            JournalEntryValidationError: If validation fails and raise_exception is True.
        """
        if not isinstance(txs_qs, TransactionModelQuerySet):
            raise JournalEntryValidationError('Must pass an instance of TransactionModelQuerySet')

        is_valid = all(tx.journal_entry_id == self.uuid for tx in txs_qs)
        if not is_valid and raise_exception:
            raise JournalEntryValidationError(
                f'Invalid TransactionModelQuerySet. All transactions must be associated with Journal Entry {self.uuid}.'
            )
        return is_valid

    def is_cash_involved(self, txs_qs: Optional[TransactionModelQuerySet] = None) -> bool:
        """
        Checks if the transactions involve cash assets.

        Parameters:
            txs_qs (Optional[TransactionModelQuerySet]): Transactions to evaluate. If None, defaults to class behavior.

        Returns:
            bool: True if cash assets are involved, otherwise False.
        """
        return roles.ASSET_CA_CASH in self.get_txs_roles(txs_qs)

    def is_operating(self) -> bool:
        """
        Checks if the Journal Entry is categorized as an operating activity.

        Returns:
            bool: True if the activity is operating, otherwise False.
        """
        return self.activity in [self.OPERATING_ACTIVITY]

    def is_financing(self) -> bool:
        """
        Checks if the Journal Entry is categorized as a financing activity.

        Returns:
            bool: True if the activity is financing, otherwise False.
        """
        return self.activity in [
            self.FINANCING_EQUITY,
            self.FINANCING_LTD,
            self.FINANCING_DIVIDENDS,
            self.FINANCING_STD,
            self.FINANCING_OTHER
        ]

    def is_investing(self) -> bool:
        """
        Checks if the Journal Entry is categorized as an investing activity.

        Returns:
            bool: True if the activity is investing, otherwise False.
        """
        return self.activity in [
            self.INVESTING_SECURITIES,
            self.INVESTING_PPE,
            self.INVESTING_OTHER
        ]

    def get_entity_unit_name(self, no_unit_name: str = "") -> str:
        """
        Retrieves the name of the entity unit associated with the Journal Entry.

        Parameters:
            no_unit_name (str): The fallback name to return if no unit is associated.

        Returns:
            str: The name of the entity unit, or the fallback provided.
        """
        if self.entity_unit_id:
            return self.entity_unit.name
        return no_unit_name

    def get_entity_last_closing_date(self) -> Optional[date]:
        """
        Retrieves the last closing date for the entity associated with the Journal Entry.

        Returns:
            Optional[date]: The last closing date if one exists, otherwise None.
        """
        try:
            return getattr(self, '_entity_last_closing_date')
        except AttributeError:
            pass
        return self.ledger.entity.last_closing_date

    def mark_as_posted(self,
                       commit: bool = False,
                       verify: bool = True,
                       force_lock: bool = False,
                       raise_exception: bool = False,
                       **kwargs):
        """
        Posted transactions show on the EntityModel ledger and financial statements.
        Parameters
        ----------
        commit: bool
            Commits changes into the Database, Defaults to False.
        verify: bool
            Verifies JournalEntryModel before marking as posted. Defaults to False.
        force_lock: bool
            Forces to lock the JournalEntry before is posted.
        raise_exception: bool
            Raises JournalEntryValidationError if cannot post. Defaults to False.
        kwargs: dict
            Additional keyword arguments.
        """
        if verify and not self.is_verified():
            txs_qs, verified = self.verify()
            if not len(txs_qs):
                if raise_exception:
                    raise JournalEntryValidationError(
                        message=_('Cannot post an empty Journal Entry.')
                    )
                return
        if force_lock and not self.is_locked():
            try:
                self.mark_as_locked(commit=False, raise_exception=True)
            except JournalEntryValidationError as e:
                if raise_exception:
                    raise e
                return
        if not self.can_post(ignore_verify=False):
            if raise_exception:
                raise JournalEntryValidationError(f'Journal Entry {self.uuid} cannot post.'
                                                  f' Is verified: {self.is_verified()}')
            return
        if not self.is_posted():
            self.posted = True
            if self.is_posted():
                if commit:
                    self.save(verify=False,
                              update_fields=[
                                  'posted',
                                  'locked',
                                  'activity',
                                  'updated'
                              ])
            journal_entry_posted.send_robust(sender=self.__class__,
                                             instance=self,
                                             commited=commit,
                                             **kwargs)

    def post(self, **kwargs):
        """
        Proxy function for `mark_as_posted` method.
        """
        return self.mark_as_posted(**kwargs)

    def mark_as_unposted(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        """
        Un-posted JournalEntryModels do not show on the EntityModel ledger and financial statements.

        Parameters
        ----------
        commit: bool
            Commits changes into the Database, Defaults to False.
        raise_exception: bool
            Raises JournalEntryValidationError if cannot post. Defaults to False.
        kwargs: dict
            Additional keyword arguments.
        """
        if not self.can_unpost():
            if raise_exception:
                raise JournalEntryValidationError(f'Journal Entry {self.uuid} cannot unpost.')
            return
        if self.is_posted():
            self.posted = False
            self.activity = None
            if not self.is_posted():
                if commit:
                    self.save(
                        verify=False,
                        update_fields=[
                            'posted',
                            'activity',
                            'updated'
                        ]
                    )
            journal_entry_unposted.send_robust(sender=self.__class__,
                                               instance=self,
                                               commited=commit,
                                               **kwargs)

    def unpost(self, **kwargs):
        """
        Proxy function for `mark_as_unposted` method.
        """
        return self.mark_as_unposted(**kwargs)

    def mark_as_locked(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        """
        Locked JournalEntryModels do not allow transactions to be edited.

        Parameters
        ----------
        commit: bool
            Commits changes into the Database, Defaults to False.
        raise_exception: bool
            Raises JournalEntryValidationError if cannot lock. Defaults to False.
        kwargs: dict
            Additional keyword arguments.
        """
        if not self.can_lock():
            if raise_exception:
                if raise_exception:
                    raise JournalEntryValidationError(f'Journal Entry {self.uuid} is already locked.')
                return
        if not self.is_locked():
            self.generate_activity(force_update=True)
            self.locked = True
            if self.is_locked():
                if commit:
                    self.save(verify=False)
                journal_entry_locked.send_robust(sender=self.__class__,
                                                 instance=self,
                                                 commited=commit,
                                                 **kwargs)

    def lock(self, **kwargs):
        """
        Proxy function for `mark_as_locked` method.
        """
        return self.mark_as_locked(**kwargs)

    def mark_as_unlocked(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        """
        Unlocked JournalEntryModels allow transactions to be edited.

        Parameters
        ----------
        commit: bool
            Commits changes into the Database, Defaults to False.
        raise_exception: bool
            Raises JournalEntryValidationError if cannot lock. Defaults to False.
        kwargs: dict
            Additional keyword arguments.
        """
        if not self.can_unlock():
            if raise_exception:
                raise JournalEntryValidationError(f'Journal Entry {self.uuid} is already unlocked.')
            return
        if self.is_locked():
            self.locked = False
            self.activity = None
            if not self.is_locked():
                if commit:
                    self.save(verify=False)
                journal_entry_unlocked.send_robust(sender=self.__class__,
                                                   instance=self,
                                                   commited=commit,
                                                   **kwargs)

    def unlock(self, **kwargs):
        """
        Proxy function for `mark_as_unlocked` method.
        """
        return self.mark_as_unlocked(**kwargs)

    def get_transaction_queryset(self, select_accounts: bool = True) -> TransactionModelQuerySet:
        """
        Retrieves the `TransactionModelQuerySet` associated with this `JournalEntryModel` instance.

        Parameters
        ----------
        select_accounts : bool, optional
            If True, prefetches the related `AccountModel` for each transaction. Defaults to True.

        Returns
        -------
        TransactionModelQuerySet
            A queryset containing transactions related to this journal entry. If `select_accounts` is
            True, the accounts are included in the query as well.
        """
        if select_accounts:
            return self.transactionmodel_set.all().select_related('account')
        return self.transactionmodel_set.all()

    def get_txs_balances(
            self,
            txs_qs: Optional[TransactionModelQuerySet] = None,
            as_dict: bool = False
    ) -> Union[TransactionModelQuerySet, Dict[str, Decimal]]:
        """
        Calculates the total CREDIT and DEBIT balances for the journal entry.

        This method performs an aggregate database query to compute the sum of CREDITs and
        DEBITs across the transactions related to this journal entry. Optionally, a pre-fetched
        `TransactionModelQuerySet` can be supplied for efficiency. Validation is performed to
        ensure that all transactions belong to this journal entry.

        Parameters
        ----------
        txs_qs : TransactionModelQuerySet, optional
            A pre-fetched queryset of transactions. If None, the queryset is fetched automatically.
        as_dict : bool, optional
            If True, returns the results as a dictionary with keys "credit" and "debit". Defaults to False.

        Returns
        -------
        Union[TransactionModelQuerySet, Dict[str, Decimal]]
            If `as_dict` is False, returns a queryset of aggregated balances. If `as_dict` is True,
            returns a dictionary containing the CREDIT and DEBIT totals.

        Raises
        ------
        JournalEntryValidationError
            If the provided queryset is invalid or does not belong to this journal entry.
        """
        if not txs_qs:
            txs_qs = self.get_transaction_queryset(select_accounts=False)
        elif not isinstance(txs_qs, TransactionModelQuerySet):
            raise JournalEntryValidationError(
                f"Expected a TransactionModelQuerySet, got {type(txs_qs).__name__}"
            )
        elif not self.is_txs_qs_valid(txs_qs):
            raise JournalEntryValidationError(
                "Invalid TransactionModelQuerySet. All transactions must belong to the same journal entry."
            )

        balances = txs_qs.values('tx_type').annotate(
            amount__sum=Coalesce(Sum('amount'), Decimal('0.00'), output_field=models.DecimalField())
        )

        if as_dict:
            return {tx['tx_type']: tx['amount__sum'] for tx in balances}
        return balances

    def get_txs_roles(
            self,
            txs_qs: Optional[TransactionModelQuerySet] = None,
            exclude_cash_role: bool = False
    ) -> Set[str]:
        """
        Retrieves the set of account roles involved in the journal entry's transactions.

        This method extracts the roles associated with the accounts linked to each transaction.
        Optionally, the CASH role can be excluded from the results.

        Parameters
        ----------
        txs_qs : TransactionModelQuerySet, optional
            A pre-fetched queryset of transactions. If None, the queryset is fetched automatically.
        exclude_cash_role : bool, optional
            If True, excludes the CASH role from the result. Defaults to False.

        Returns
        -------
        Set[str]
            A set of account roles associated with this journal entry's transactions.
        """
        if not txs_qs:
            txs_qs = self.get_transaction_queryset(select_accounts=True)
        else:
            self.is_txs_qs_valid(txs_qs)

        roles = {tx.account.role for tx in txs_qs}

        if exclude_cash_role:
            roles.discard(ASSET_CA_CASH)

        return roles

    def has_activity(self) -> bool:
        """
        Checks if the journal entry has an associated activity.

        Returns
        -------
        bool
            True if an activity is defined for the journal entry, otherwise False.
        """
        return self.activity is not None

    def get_activity_name(self) -> Optional[str]:
        """
        Gets the name of the activity associated with this journal entry.

        The activity indicates its categorization based on GAAP (e.g., operating, investing, financing).

        Returns
        -------
        Optional[str]
            The activity name if defined, otherwise None.
        """
        if self.activity:
            if self.is_operating():
                return ActivityEnum.OPERATING.value
            elif self.is_investing():
                return ActivityEnum.INVESTING.value
            elif self.is_financing():
                return ActivityEnum.FINANCING.value
        return None

    @classmethod
    def get_activity_from_roles(
            cls,
            role_set: Union[List[str], Set[str]],
            validate: bool = False,
            raise_exception: bool = True
    ) -> Optional[str]:
        """
        Determines the financial activity type (e.g., operating, investing, financing)
        based on a set of account roles.

        Parameters
        ----------
        role_set : Union[List[str], Set[str]]
            The set of roles to analyze.
        validate : bool, optional
            If True, validates the roles before analysis. Defaults to False.
        raise_exception : bool, optional
            If True, raises an exception if multiple activities are detected. Defaults to True.

        Returns
        -------
        Optional[str]
            The detected activity name, or None if no activity type is matched.

        Raises
        ------
        JournalEntryValidationError
            If multiple activities are detected and `raise_exception` is True.
        """
        if validate:
            role_set = validate_roles(roles=role_set)
        else:
            if isinstance(role_set, list):
                role_set = set(role_set)

        activity = None

        # no roles involved
        if not len(role_set):
            return

        # determining if investing....
        is_investing_for_ppe = all([
            # all roles must be in group
            all([r in GROUP_CFS_INVESTING_PPE for r in role_set]),
            # at least one role
            sum([r in GROUP_CFS_INVESTING_PPE for r in role_set]) > 0,
            # at least one role
            # sum([r in GROUP_CFS_INV_LTD_OF_PPE for r in role_set]) > 0,
        ])
        is_investing_for_securities = all([
            # all roles must be in group
            all([r in GROUP_CFS_INVESTING_SECURITIES for r in role_set]),
            # at least one role
            sum([r in GROUP_CFS_INVESTING_SECURITIES for r in role_set]) > 0,
            # at least one role
            # sum([r in GROUP_CFS_INV_LTD_OF_SECURITIES for r in role_set]) > 0,
        ])

        # IS INVESTING OTHERS....?

        # determining if financing...
        is_financing_dividends = all([r in GROUP_CFS_FIN_DIVIDENDS for r in role_set])
        is_financing_issuing_equity = all([r in GROUP_CFS_FIN_ISSUING_EQUITY for r in role_set])
        is_financing_st_debt = all([r in GROUP_CFS_FIN_ST_DEBT_PAYMENTS for r in role_set])
        is_financing_lt_debt = all([r in GROUP_CFS_FIN_LT_DEBT_PAYMENTS for r in role_set])

        is_operating = all([r not in GROUP_CFS_INVESTING_AND_FINANCING for r in role_set])

        if sum([
            is_investing_for_ppe,
            is_investing_for_securities,
            is_financing_lt_debt,
            is_financing_st_debt,
            is_financing_issuing_equity,
            is_financing_dividends,
            is_operating
        ]) > 1:
            if raise_exception:
                raise JournalEntryValidationError(
                    f'Multiple activities detected in roles JE {role_set}.')
        else:
            if is_investing_for_ppe:
                activity = cls.INVESTING_PPE
            elif is_investing_for_securities:
                activity = cls.INVESTING_SECURITIES
            elif is_financing_st_debt:
                activity = cls.FINANCING_STD
            elif is_financing_lt_debt:
                activity = cls.FINANCING_LTD
            elif is_financing_issuing_equity:
                activity = cls.FINANCING_EQUITY
            elif is_financing_dividends:
                activity = cls.FINANCING_DIVIDENDS
            elif is_operating:
                activity = cls.OPERATING_ACTIVITY
            else:
                if raise_exception:
                    raise JournalEntryValidationError(f'No activity match for roles {role_set}.'
                                                      'Split into multiple Journal Entries or check'
                                                      ' your account selection.')
        return activity

    def generate_activity(self,
                          txs_qs: Optional[TransactionModelQuerySet] = None,
                          raise_exception: bool = True,
                          force_update: bool = False) -> Optional[str]:
        """
        Generates the activity for the Journal Entry model based on its transactions.

        Parameters
        ----------
        txs_qs : Optional[TransactionModelQuerySet], default None
            Queryset of TransactionModel instances for validation. If None, transactions are queried.
        raise_exception : bool, default True
            Determines whether exceptions are raised during processing.
        force_update : bool, default False
            Forces the regeneration of activity even if it exists.

        Returns
        -------
        Optional[str]
            Generated activity or None if not applicable.
        """
        if not self._state.adding:
            if raise_exception and self.is_closing_entry:
                raise_exception = False

            if any([
                not self.has_activity(),
                not self.is_locked(),
                force_update
            ]):

                txs_is_valid = True
                if not txs_qs:
                    txs_qs = self.get_transaction_queryset(select_accounts=False)
                else:
                    try:
                        txs_is_valid = self.is_txs_qs_valid(txs_qs=txs_qs, raise_exception=raise_exception)
                    except JournalEntryValidationError as e:
                        if raise_exception:
                            raise e

                if txs_is_valid:
                    cash_is_involved = self.is_cash_involved(txs_qs=txs_qs)
                    if not cash_is_involved:
                        self.activity = None
                    else:
                        role_list = self.get_txs_roles(txs_qs, exclude_cash_role=True)
                        self.activity = self.get_activity_from_roles(
                            role_set=role_list,
                            raise_exception=raise_exception
                        )
        return self.activity

    # todo: add entity_model as parameter on all functions...
    # todo: outsource this function to EntityStateModel...?...
    def _get_next_state_model(self, raise_exception: bool = True) -> Optional[EntityStateModel]:
        """
        Retrieves or creates the next state model for the Journal Entry.

        Parameters
        ----------
        raise_exception : bool, default True
            Determines if exceptions should be raised when the entity state is not found.

        Returns
        -------
        EntityStateModel
            The state model with an incremented sequence.
        """
        entity_model = self.entity_model
        fy_key = entity_model.get_fy_for_date(dt=self.timestamp)

        try:
            LOOKUP = {
                'entity_model_id__exact': self.entity_uuid,
                'entity_unit_id__exact': self.entity_unit_id,
                'fiscal_year': fy_key,
                'key__exact': EntityStateModel.KEY_JOURNAL_ENTRY
            }

            state_model_qs = EntityStateModel.objects.filter(**LOOKUP).select_related(
                'entity_model').select_for_update()
            state_model = state_model_qs.get()
            state_model.sequence = F('sequence') + 1
            state_model.save()
            state_model.refresh_from_db()
            return state_model

        except ObjectDoesNotExist:
            LOOKUP = {
                'entity_model_id': entity_model.uuid,
                'entity_unit_id': self.entity_unit_id,
                'fiscal_year': fy_key,
                'key': EntityStateModel.KEY_JOURNAL_ENTRY,
                'sequence': 1
            }
            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model

        except IntegrityError as e:
            if raise_exception:
                raise e

    def can_generate_je_number(self) -> bool:
        """
        Checks if a Journal Entry Number can be generated.

        Returns
        -------
        bool
            True if the Journal Entry can generate a JE number, otherwise False.
        """
        return all([
            self.ledger_id,
            not self.je_number
        ])

    def generate_je_number(self, commit: bool = False) -> str:
        """
        Generates the Journal Entry number in an atomic transaction.

        Parameters
        ----------
        commit : bool, default False
            Saves the generated JE number in the database.

        Returns
        -------
        str
            The generated or existing JE number.
        """
        if self.can_generate_je_number():

            with transaction.atomic():

                state_model = None
                while not state_model:
                    state_model = self._get_next_state_model(raise_exception=False)

                if self.entity_unit_id:
                    unit_prefix = self.entity_unit.document_prefix
                else:
                    unit_prefix = DJANGO_LEDGER_JE_NUMBER_NO_UNIT_PREFIX

                seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
                self.je_number = f'{DJANGO_LEDGER_JE_NUMBER_PREFIX}-{state_model.fiscal_year}-{unit_prefix}-{seq}'

                if commit:
                    self.save(update_fields=['je_number'])

        return self.je_number

    def verify(self,
               txs_qs: Optional[TransactionModelQuerySet] = None,
               force_verify: bool = False,
               raise_exception: bool = True,
               **kwargs) -> Tuple[TransactionModelQuerySet, bool]:

        """
        Verifies the validity of the Journal Entry model instance.

        Parameters
        ----------
        txs_qs : Optional[TransactionModelQuerySet], default None
            Queryset of TransactionModel instances to validate. If None, transactions are queried.
        force_verify : bool, default False
            Forces re-verification even if already verified.
        raise_exception : bool, default True
            Determines if exceptions are raised on validation failure.
        kwargs : dict
            Additional options.

        Returns
        -------
        Tuple[TransactionModelQuerySet, bool]
            - The TransactionModelQuerySet associated with the JournalEntryModel.
            - A boolean indicating whether verification was successful.
        """

        if not self.is_verified() or force_verify:
            self._verified = False

            # fetches JEModel TXS QuerySet if not provided....
            if not txs_qs:
                txs_qs = self.get_transaction_queryset()
                is_txs_qs_valid = True
            else:
                try:
                    # if provided, it is verified...
                    is_txs_qs_valid = self.is_txs_qs_valid(raise_exception=raise_exception, txs_qs=txs_qs)
                except JournalEntryValidationError as e:
                    raise e

            # CREDIT/DEBIT Balance validation...
            try:
                is_balance_valid = self.is_balance_valid(txs_qs=txs_qs)
                if not is_balance_valid:
                    raise JournalEntryValidationError('Transaction balances are not valid!')
            except JournalEntryValidationError as e:
                raise e

            # Transaction CoA if valid...

            try:
                is_coa_valid = self.is_txs_qs_coa_valid(txs_qs=txs_qs)
                if not is_coa_valid:
                    raise JournalEntryValidationError('Transaction COA is not valid!')
            except JournalEntryValidationError as e:
                raise e

            # if not len(txs_qs):
            #     if raise_exception:
            #         raise JournalEntryValidationError('Journal entry has no transactions.')

            # if len(txs_qs) < 2:
            #     if raise_exception:
            #         raise JournalEntryValidationError('At least two transactions required.')

            if all([
                is_balance_valid,
                is_txs_qs_valid,
                is_coa_valid
            ]):
                # activity flag...
                self.generate_activity(txs_qs=txs_qs, raise_exception=raise_exception)
                self._verified = True
                return txs_qs, self.is_verified()
        return self.get_transaction_queryset(), self.is_verified()

    def clean(self,
              verify: bool = False,
              raise_exception: bool = True,
              txs_qs: Optional[TransactionModelQuerySet] = None) -> Tuple[TransactionModelQuerySet, bool]:
        """
        Cleans the JournalEntryModel instance, optionally verifying it and generating a Journal Entry (JE) number if required.

        Parameters
        ----------
        verify : bool, optional
            If True, attempts to verify the JournalEntryModel during the cleaning process. Default is False.
        raise_exception : bool, optional
            If True, raises an exception when the instance fails verification. Default is True.
        txs_qs : TransactionModelQuerySet, optional
            A pre-fetched TransactionModelQuerySet. If provided, avoids additional database queries. The provided queryset is
            validated against the JournalEntryModel instance.

        Returns
        -------
        Tuple[TransactionModelQuerySet, bool]
            A tuple containing:
            - The validated TransactionModelQuerySet for the JournalEntryModel instance.
            - A boolean indicating whether the instance passed verification.

        Raises
        ------
        JournalEntryValidationError
            If the instance has a timestamp in the future and is posted, or if verification fails and `raise_exception` is True.
        """

        if txs_qs:
            self.is_txs_qs_valid(txs_qs=txs_qs)

        if not self.timestamp:
            self.timestamp = get_localtime()
        elif all([
            self.timestamp,
            self.timestamp > get_localtime(),
            self.is_posted()
        ]):
            raise JournalEntryValidationError(message='Cannot Post JE Models with timestamp in the future.')

        self.generate_je_number(commit=True)
        if verify:
            txs_qs, verified = self.verify()
            return txs_qs, self.is_verified()
        return self.get_transaction_queryset(), self.is_verified()

    def get_delete_message(self) -> str:
        """
        Generates a confirmation message for deleting the JournalEntryModel instance.

        Returns
        -------
        str
            A confirmation message including the Journal Entry number and Ledger name.
        """
        return _(f'Are you sure you want to delete JournalEntry Model {self.je_number} on Ledger {self.ledger.name}?')

    def delete(self, **kwargs):
        """
        Deletes the JournalEntryModel instance, ensuring it is allowed to be deleted.

        Parameters
        ----------
        **kwargs : dict
            Additional arguments passed to the parent delete method.

        Raises
        ------
        JournalEntryValidationError
            If the instance is not eligible for deletion.
        """
        if not self.can_delete():
            raise JournalEntryValidationError(
                message=_(f'JournalEntryModel {self.uuid} cannot be deleted...')
            )
        return super().delete(**kwargs)

    def save(
            self,
            verify: bool = True,
            post_on_verify: bool = False,
            *args,
            **kwargs
    ):
        """
        Saves the JournalEntryModel instance, with optional verification and posting prior to saving.

        Parameters
        ----------
        verify : bool, optional
            If True, verifies the transactions of the JournalEntryModel before saving. Default is True.
        post_on_verify : bool, optional
            If True, posts the JournalEntryModel if verification is successful and `can_post()` is True. Default is False.

        Returns
        -------
        JournalEntryModel
            The saved JournalEntryModel instance.

        Raises
        ------
        JournalEntryValidationError
            If the instance fails verification or encounters an issue during save.
        """
        try:
            # Generate the Journal Entry number prior to verification and saving
            self.generate_je_number(commit=False)

            if verify:
                txs_qs, is_verified = self.clean(verify=True)
                if is_verified and post_on_verify:
                    # Mark as posted if verification succeeds and posting is requested
                    self.mark_as_posted(commit=False, verify=False, force_lock=True, raise_exception=True)

        except ValidationError as e:
            if self.can_unpost():
                self.mark_as_unposted(raise_exception=True)
            raise JournalEntryValidationError(
                f'Error validating Journal Entry ID: {self.uuid}: {e.message}'
            )
        except Exception as e:
            # Safety net for unexpected errors during save
            self.posted = False
            self._verified = False
            self.save(update_fields=['posted', 'updated'], verify=False)
            raise JournalEntryValidationError(e)

        # Prevent saving an unverified Journal Entry
        if not self.is_verified() and verify:
            raise JournalEntryValidationError(message='Cannot save an unverified Journal Entry.')

        return super(JournalEntryModelAbstract, self).save(*args, **kwargs)

    # URLS Generation...

    def get_absolute_url(self) -> str:
        """
        Generates the URL to view the details of the journal entry.

        Returns
        -------
        str
            The absolute URL for the journal entry details.
        """
        return reverse('django_ledger:je-detail', kwargs={
            'je_pk': self.uuid,
            'ledger_pk': self.ledger_id,
            'entity_slug': self.entity_slug
        })

    def get_detail_url(self) -> str:
        """
        Generates the detail URL for the journal entry.

        Returns
        -------
        str
            The URL for updating or viewing journal entry details.
        """
        return self.get_absolute_url()

    def get_journal_entry_list_url(self) -> str:
        """
        Constructs the URL to access the list of journal entries
        associated with a specific ledger and entity.

        Returns
        -------
        str
            The URL for the journal entry list.
        """
        return reverse('django_ledger:je-list', kwargs={
            'entity_slug': self.entity_slug,
            'ledger_pk': self.ledger_id
        })

    def get_journal_entry_create_url(self) -> str:
        """
        Constructs the URL to create a new journal entry
        associated with a specific ledger and entity.

        Returns
        -------
        str
            The URL to create a journal entry.
        """
        return reverse('django_ledger:je-create', kwargs={
            'entity_slug': self.entity_slug,
            'ledger_pk': self.ledger_id
        })

    def get_detail_txs_url(self) -> str:
        """
        Generates the URL to view transaction details of the journal entry.

        Returns
        -------
        str
            The URL for transaction details of the journal entry.
        """
        return reverse('django_ledger:je-detail-txs', kwargs={
            'entity_slug': self.entity_slug,
            'ledger_pk': self.ledger_id,
            'je_pk': self.uuid
        })

    def get_unlock_url(self) -> str:
        """
        Generates the URL to mark the journal entry as unlocked.

        Returns
        -------
        str
            The URL for unlocking the journal entry.
        """
        return reverse('django_ledger:je-mark-as-unlocked', kwargs={
            'entity_slug': self.entity_slug,
            'ledger_pk': self.ledger_id,
            'je_pk': self.uuid
        })

    def get_lock_url(self) -> str:
        """
        Generates the URL to mark the journal entry as locked.

        Returns
        -------
        str
            The URL for locking the journal entry.
        """
        return reverse('django_ledger:je-mark-as-locked', kwargs={
            'entity_slug': self.entity_slug,
            'ledger_pk': self.ledger_id,
            'je_pk': self.uuid
        })

    def get_post_url(self) -> str:
        """
        Generates the URL to mark the journal entry as posted.

        Returns
        -------
        str
            The URL for posting the journal entry.
        """
        return reverse('django_ledger:je-mark-as-posted', kwargs={
            'entity_slug': self.entity_slug,
            'ledger_pk': self.ledger_id,
            'je_pk': self.uuid
        })

    def get_unpost_url(self) -> str:
        """
        Generates the URL to mark the journal entry as unposted.

        Returns
        -------
        str
            The URL for unposting the journal entry.
        """
        return reverse('django_ledger:je-mark-as-unposted', kwargs={
            'entity_slug': self.entity_slug,
            'ledger_pk': self.ledger_id,
            'je_pk': self.uuid
        })

    # Action URLS....
    def get_action_post_url(self) -> str:
        """
        Generates the URL used to mark the journal entry as posted.

        Returns
        -------
        str
            The generated URL for marking the journal entry as posted.
        """
        return reverse('django_ledger:je-mark-as-posted',
                       kwargs={
                           'entity_slug': self.entity_slug,
                           'ledger_pk': self.ledger_id,
                           'je_pk': self.uuid
                       })

    def get_action_unpost_url(self) -> str:
        """
        Generates the URL used to mark the journal entry as unposted.

        Returns
        -------
        str
            The generated URL for marking the journal entry as unposted.
        """
        return reverse('django_ledger:je-mark-as-unposted',
                       kwargs={
                           'entity_slug': self.entity_slug,
                           'ledger_pk': self.ledger_id,
                           'je_pk': self.uuid
                       })

    def get_action_lock_url(self) -> str:
        """
        Generates the URL used to mark the journal entry as locked.

        Returns
        -------
        str
            The generated URL for marking the journal entry as locked.
        """
        return reverse('django_ledger:je-mark-as-locked',
                       kwargs={
                           'entity_slug': self.entity_slug,
                           'ledger_pk': self.ledger_id,
                           'je_pk': self.uuid
                       })

    def get_action_unlock_url(self) -> str:
        """
        Generates the URL used to mark the journal entry as unlocked.

        Returns
        -------
        str
            The generated URL for marking the journal entry as unlocked.
        """
        return reverse('django_ledger:je-mark-as-unlocked',
                       kwargs={
                           'entity_slug': self.entity_slug,
                           'ledger_pk': self.ledger_id,
                           'je_pk': self.uuid
                       })


class JournalEntryModel(JournalEntryModelAbstract):
    """
    Journal Entry Model Base Class From Abstract
    """

    class Meta(JournalEntryModelAbstract.Meta):
        abstract = False


def journalentrymodel_presave(instance: JournalEntryModel, **kwargs):
    if instance._state.adding:
        # cannot add journal entries to a locked ledger...
        if instance.ledger_is_locked():
            raise JournalEntryValidationError(
                message=_(f'Cannot add Journal Entries to locked LedgerModel {instance.ledger_id}')
            )
    instance.generate_je_number(commit=False)


pre_save.connect(journalentrymodel_presave, sender=JournalEntryModel)
