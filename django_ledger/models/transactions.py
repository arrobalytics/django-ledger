"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

The TransactionModel serves as the foundational accounting entity where all financial transactions are recorded.
Every transaction must be associated with a JournalEntryModel, which represents a collection
of related transactions. This strict association ensures that standalone TransactionModels—or orphan transactions—do not
exist, a constraint enforced at the database level.

Each transaction performs either a CREDIT or a DEBIT operation on the designated AccountModel, upholding standard
accounting principles. The TransactionModel API integrates the IOMixIn, a critical component for generating financial
statements. This mixin facilitates efficient querying and aggregation directly at the database level, eliminating the need
to load all TransactionModels into memory. This database-driven approach significantly improves performance and simplifies
the process of generating accurate financial reports.

The TransactionModel, together with the IOMixIn, is essential for ensuring seamless, efficient, and reliable
financial statement production in the Django Ledger framework.
"""
import warnings
from datetime import datetime, date
from typing import List, Union, Set
from uuid import uuid4, UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, QuerySet, Manager, F
from django.db.models.signals import pre_save
from django.utils.translation import gettext_lazy as _

from django_ledger.io.io_core import validate_io_timestamp
from django_ledger.models import AccountModel, BillModel, EntityModel, InvoiceModel, LedgerModel
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.unit import EntityUnitModel
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR

UserModel = get_user_model()


class TransactionModelValidationError(ValidationError):
    pass


class TransactionModelQuerySet(QuerySet):
    """
    A custom QuerySet class tailored for `TransactionModel` objects. It includes a collection
    of methods to efficiently and safely retrieve and filter transactions from the database
    based on common use cases.
    """

    def for_user(self, user_model) -> 'TransactionModelQuerySet':
        """
        Filters transactions accessible to a specific user based on their permissions.

        Parameters
        ----------
        user_model : UserModel
            The user object for which the transactions should be filtered.

        Returns
        -------
        TransactionModelQuerySet
            A queryset containing transactions filtered by the user's access level.

        Description
        -----------
        - Returns all `TransactionModel` objects for superusers.
        - For regular users, it filters transactions where:
          - The user is an admin of the entity associated with the ledger in the transaction.
          - The user is a manager of the entity associated with the ledger in the transaction.
        """

        if user_model.is_superuser:
            return self

        return self.filter(
            Q(journal_entry__ledger__entity__admin=user_model) |
            Q(journal_entry__ledger__entity__managers__in=[user_model])
        )

    def posted(self) -> 'TransactionModelQuerySet':
        """
        Retrieves transactions that are part of a posted journal entry and ledger.

        A transaction is considered "posted" if:
        - It belongs to a journal entry marked as *posted*.
        - Its associated journal entry is part of a ledger marked as *posted*.

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet containing only transactions that meet the "posted" criteria.
        """
        return self.filter(
            Q(journal_entry__posted=True) &
            Q(journal_entry__ledger__posted=True)
        )

    def for_accounts(self, account_list: List[Union[AccountModel, str, UUID]]) -> 'TransactionModelQuerySet':
        """
        Filters transactions based on the accounts they are associated with.

        Parameters
        ----------
        account_list : list of str or AccountModel
            A list containing account codes (strings) or `AccountModel` instances.
            Transactions will be filtered to match these accounts.

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet filtered for transactions associated with the specified accounts.
        """

        if not isinstance(account_list, list) or not len(account_list) > 0:
            raise TransactionModelValidationError(
                message=_('Account list must be a list of AccountModel, UUID or str objects (codes).')
            )
        if isinstance(account_list[0], str):
            return self.filter(account__code__in=account_list)
        elif isinstance(account_list[0], UUID):
            return self.filter(account__uuid__in=account_list)
        elif isinstance(account_list[0], AccountModel):
            return self.filter(account__in=account_list)
        raise TransactionModelValidationError(
            message=_('Account list must be a list of AccountModel, UUID or str objects (codes).')
        )

    def for_roles(self, role_list: Union[str, List[str], Set[str]]) -> 'TransactionModelQuerySet':
        """
        Fetches a QuerySet of TransactionModels which AccountModel has a specific role.

        Parameters
        ----------
        role_list: str or list
            A string or list of strings representing the roles to be used as filter.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
        """
        if isinstance(role_list, str):
            return self.filter(account__role__in=[role_list])
        return self.filter(account__role__in=role_list)

    def for_unit(self, unit_slug: Union[str, EntityUnitModel]) -> 'TransactionModelQuerySet':
        """
        Filters transactions based on their associated entity unit.

        Parameters
        ----------
        unit_slug : str or EntityUnitModel
            A string representing the slug of the entity unit or an `EntityUnitModel` instance.

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet filtered for transactions linked to the specified unit.
        """
        if isinstance(unit_slug, EntityUnitModel):
            return self.filter(journal_entry__entity_unit=unit_slug)
        return self.filter(journal_entry__entity_unit__slug__exact=unit_slug)

    def for_activity(self, activity_list: Union[str, List[str], Set[str]]) -> 'TransactionModelQuerySet':
        """
        Filters transactions based on their associated activity or activities.

        Parameters
        ----------
        activity_list : str or list of str
            A single activity or a list of activities to filter transactions by.

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet filtered for transactions linked to the specified activity or activities.
        """
        if isinstance(activity_list, str):
            return self.filter(journal_entry__activity__in=[activity_list])
        return self.filter(journal_entry__activity__in=activity_list)

    def to_date(self, to_date: Union[str, date, datetime]) -> 'TransactionModelQuerySet':
        """
        Filters transactions occurring on or before a specific date or timestamp.

        If `to_date` is a naive datetime (no timezone), it is assumed to be in local time
        based on Django settings.

        Parameters
        ----------
        to_date : str, date, or datetime
            The maximum date or timestamp for filtering. When using a date (not datetime),
            the filter is inclusive (e.g., "2022-12-20" includes all transactions from that day).

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet filtered to include transactions up to the specified date or timestamp.
        """

        if isinstance(to_date, str):
            to_date = validate_io_timestamp(to_date)

        if isinstance(to_date, date):
            return self.filter(journal_entry__timestamp__date__lte=to_date)
        return self.filter(journal_entry__timestamp__lte=to_date)

    def from_date(self, from_date: Union[str, date, datetime]) -> 'TransactionModelQuerySet':
        """
        Filters transactions occurring on or after a specific date or timestamp.

        If `from_date` is a naive datetime (no timezone), it is assumed to be in local time
        based on Django settings.

        Parameters
        ----------
        from_date : str, date, or datetime
            The minimum date or timestamp for filtering. When using a date (not datetime),
            the filter is inclusive (e.g., "2022-12-20" includes all transactions from that day).

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet filtered to include transactions from the specified date or timestamp onwards.
        """
        if isinstance(from_date, str):
            from_date = validate_io_timestamp(from_date)

        if isinstance(from_date, date):
            return self.filter(journal_entry__timestamp__date__gte=from_date)

        return self.filter(journal_entry__timestamp__gte=from_date)

    def not_closing_entry(self) -> 'TransactionModelQuerySet':
        """
        Filters transactions that are *not* part of a closing journal entry.

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet with transactions where the `journal_entry__is_closing_entry` field is False.
        """
        return self.filter(journal_entry__is_closing_entry=False)

    def is_closing_entry(self) -> 'TransactionModelQuerySet':
        """
        Filters transactions that are part of a closing journal entry.

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet with transactions where the `journal_entry__is_closing_entry` field is True.
        """
        return self.filter(journal_entry__is_closing_entry=True)

    def for_ledger(self, ledger_model: Union[LedgerModel, UUID, str]) -> 'TransactionModelQuerySet':
        """
        Filters transactions for a specific ledger under a given entity.

        Parameters
        ----------
        ledger_model : Union[LedgerModel, UUID]
            The ledger model or its UUID to filter by.

        Returns
        -------
        TransactionModelQuerySet
            A queryset containing transactions associated with the given ledger and entity.
        """
        if isinstance(ledger_model, UUID):
            return self.filter(journal_entry__ledger__uuid__exact=ledger_model)
        return self.filter(journal_entry__ledger=ledger_model)

    def for_journal_entry(self, je_model) -> 'TransactionModelQuerySet':
        """
        Filters transactions for a specific journal entry under a given ledger and entity.

        Parameters
        ----------
        je_model : Union[JournalEntryModel, UUID]
            The journal entry model or its UUID to filter by.

        Returns
        -------
        TransactionModelQuerySet
            A queryset containing transactions associated with the given journal entry.
        """
        if isinstance(je_model, lazy_loader.get_journal_entry_model()):
            return self.filter(journal_entry=je_model)
        return self.filter(journal_entry__uuid__exact=je_model)

    def for_bill(self, bill_model: Union[BillModel, str, UUID]) -> 'TransactionModelQuerySet':
        """
        Filters transactions for a specific bill under a given entity.

        Parameters
        ----------
        bill_model : Union[BillModel, str, UUID]
            The bill model or its UUID to filter by.

        Returns
        -------
        TransactionModelQuerySet
            A queryset containing transactions related to the specified bill.
        """
        if isinstance(bill_model, BillModel):
            return self.filter(journal_entry__ledger__billmodel=bill_model)
        return self.filter(journal_entry__ledger__billmodel__uuid__exact=bill_model)

    def for_invoice(self, invoice_model: Union[InvoiceModel, str, UUID]) -> 'TransactionModelQuerySet':
        """
        Filters transactions for a specific invoice under a given entity.

        Parameters
        ----------
        invoice_model : Union[InvoiceModel, str, UUID]
            The invoice model or its UUID to filter by.

        Returns
        -------
        TransactionModelQuerySet
            A queryset containing transactions related to the specified invoice.
        """
        if isinstance(invoice_model, InvoiceModel):
            return self.filter(journal_entry__ledger__invoicemodel=invoice_model)
        return self.filter(journal_entry__ledger__invoicemodel__uuid__exact=invoice_model)

    def with_annotated_details(self) -> 'TransactionModelQuerySet':
        return self.annotate(
            entity_unit_name=F('journal_entry__entity_unit__name'),
            account_code=F('account__code'),
            account_name=F('account__name'),
            timestamp=F('journal_entry__timestamp'),
        )

    def is_cleared(self) -> 'TransactionModelQuerySet':
        return self.filter(cleared=True)

    def not_cleared(self) -> 'TransactionModelQuerySet':
        return self.filter(cleared=False)

    def is_reconciled(self) -> 'TransactionModelQuerySet':
        return self.filter(reconciled=True)

    def not_reconciled(self) -> 'TransactionModelQuerySet':
        return self.filter(reconciled=False)


class TransactionModelManager(Manager):
    """
    A custom manager for `TransactionModel` designed to add helper methods for
    querying and filtering `TransactionModel` objects efficiently based on use cases like
    user permissions, associated entities, ledgers, journal entries, and more.

    This manager leverages `TransactionModelQuerySet` for complex query construction and
    integrates advanced filtering options based on user roles, entities, and other relationships.
    """

    def get_queryset(self) -> TransactionModelQuerySet:
        """
        Retrieves the base queryset for `TransactionModel`, annotated and pre-loaded
        with commonly used related fields.

        Returns
        -------
        TransactionModelQuerySet
            A custom queryset with essential annotations and relationships preloaded.
        """
        qs = TransactionModelQuerySet(self.model, using=self._db)
        return qs.annotate(
            timestamp=F('journal_entry__timestamp'),
            _coa_id=F('account__coa_model_id')  # Annotates the `coa_model_id` from the related `account`.
        ).select_related(
            'journal_entry',  # Pre-loads the related Journal Entry.
            'account',  # Pre-loads the Account associated with the Transaction.
            'account__coa_model',  # Pre-loads the Chart of Accounts related to the Account.
        )

    def for_entity(self,
                   entity_model: Union[EntityModel, str, UUID],
                   **kwargs) -> TransactionModelQuerySet:
        """
        Filters transactions for a specific entity, optionally scoped to a specific user.

        Parameters
        ----------
        entity_model : Union[EntityModel, str, UUID]
            Identifier for the entity. This can be an `EntityModel` object, a slug (str), or a UUID.

        Returns
        -------
        TransactionModelQuerySet
            A queryset containing transactions associated with the specified entity.

        Notes
        -----
        - If `user_model` is provided, only transactions accessible by the user are included.
        - Supports flexible filtering by accepting different forms of `entity_slug`.
        """

        qs = self.get_queryset()
        if 'user_model' in kwargs:
            warnings.warn(
                'user_model parameter is deprecated and will be removed in a future release. '
                'Use for_user(user_model).for_entity(entity_model) instead to keep current behavior.',
                DeprecationWarning,
                stacklevel=2
            )
            if DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR:
                qs = qs.for_user(kwargs['user_model'])

        if isinstance(entity_model, EntityModel):
            qs = qs.filter(journal_entry__ledger__entity=entity_model)
        elif isinstance(entity_model, UUID):
            qs = qs.filter(journal_entry__ledger__entity_id=entity_model)
        elif isinstance(entity_model, str):
            qs = qs.filter(journal_entry__ledger__entity__slug__exact=entity_model)
        else:
            raise TransactionModelValidationError(
                message='entity_model parameter must be either an EntityModel, String or a UUID.'
            )
        return qs


class TransactionModelAbstract(CreateUpdateMixIn):
    """
    Abstract base model class for representing financial transactions in a ledger system.

    This class defines the structure and behavior of transactions in a generic ledger system,
    including attributes such as transaction type, associated account, amount, description,
    and status flags for cleared and reconciled state. It also includes methods and properties
    to facilitate queries and determine transaction type.

    Attributes
    ----------
    uuid : UUID
        Unique identifier of the transaction.
    tx_type : str
        Type of the transaction, either 'credit' or 'debit'.
    journal_entry : ForeignKey
        Reference to the associated JournalEntryModel instance for this transaction.
    account : ForeignKey
        Reference to the associated account in the Chart of Accounts.
    amount : Decimal
        Monetary amount for the transaction. Must be a non-negative value.
    description : str, optional
        Description of the transaction.
    cleared : bool
        Indicates if the transaction has been cleared. Defaults to False.
    reconciled : bool
        Indicates if the transaction has been reconciled. Defaults to False.
    objects : TransactionModelManager
        Custom manager for managing transaction models.
    """

    CREDIT = 'credit'
    DEBIT = 'debit'
    TX_TYPE = [
        (CREDIT, _('Credit')),
        (DEBIT, _('Debit'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    tx_type = models.CharField(max_length=10, choices=TX_TYPE, verbose_name=_('Transaction Type'))

    journal_entry = models.ForeignKey(
        'django_ledger.JournalEntryModel',
        editable=False,
        verbose_name=_('Journal Entry'),
        help_text=_('Journal Entry to be associated with this transaction.'),
        on_delete=models.CASCADE
    )
    account = models.ForeignKey(
        'django_ledger.AccountModel',
        verbose_name=_('Account'),
        help_text=_('Account from Chart of Accounts to be associated with this transaction.'),
        on_delete=models.PROTECT
    )
    amount = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        default=0.00,
        verbose_name=_('Amount'),
        help_text=_('Amount of the transaction.'),
        validators=[MinValueValidator(0)]
    )
    description = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Transaction Description'),
        help_text=_('A description to be included with this individual transaction.')
    )
    cleared = models.BooleanField(default=False, verbose_name=_('Cleared'))
    reconciled = models.BooleanField(default=False, verbose_name=_('Reconciled'))
    objects = TransactionModelManager.from_queryset(TransactionModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        indexes = [
            models.Index(fields=['tx_type']),
            models.Index(fields=['account']),
            models.Index(fields=['journal_entry']),
            models.Index(fields=['created']),
            models.Index(fields=['updated']),
            models.Index(fields=['cleared']),
            models.Index(fields=['reconciled']),
        ]

    def __str__(self):
        return '{code}-{name}/{balance_type}: {amount}/{tx_type}'.format(
            code=self.account.code,
            name=self.account.name,
            balance_type=self.account.balance_type,
            amount=self.amount,
            tx_type=self.tx_type
        )

    @property
    def coa_id(self):
        """
        Returns the Chart of Accounts (COA) ID associated with the current object.

        The property attempts to retrieve the COA ID value stored internally, if it exists.
        If the internal value is not set and the `account` attribute is not `None`,
        the COA ID is obtained from the `account.coa_model_id` attribute. Otherwise,
        it will return `None`.

        Returns
        -------
        Any or None
            The COA ID if it exists, otherwise `None`.
        """
        try:
            return getattr(self, '_coa_id')
        except AttributeError:
            if self.account is None:
                return None
            return self.account.coa_model_id

    def is_debit(self):
        """
        Determines if the transaction type is a debit.

        This method checks whether the transaction type of the current instance is
        set to a debit type.

        Returns
        -------
        bool
            True if the transaction type is debit, otherwise False.
        """
        return self.tx_type == self.DEBIT

    def is_credit(self):
        """
        Check if the transaction is of type 'credit'.

        This method evaluates whether the transaction type of the current instance
        matches the 'credit' transaction type.

        Returns
        -------
        bool
            True if the transaction type is 'credit', False otherwise.
        """
        return self.tx_type == self.CREDIT


class TransactionModel(TransactionModelAbstract):
    """
    Base Transaction Model From Abstract.
    """

    class Meta(TransactionModelAbstract.Meta):
        abstract = False


def transactionmodel_presave(instance: TransactionModel, **kwargs):
    """
    Pre-save validation for the TransactionModel instance.

    This function is executed before saving a `TransactionModel` instance,
    ensuring that certain conditions are met to maintain data integrity.

    The function performs the following validations:
    1. **Account Transactionality**:
       If the `bypass_account_state` flag is not provided or set to `False`,
       it verifies whether the associated account can process transactions
       by calling `instance.account.can_transact()`. If the account cannot
       process transactions, the save operation is interrupted to prevent
       invalid data.

    2. **Journal Entry Lock**:
       If the associated journal entry (`instance.journal_entry`) is locked,
       the transaction cannot be modified. The save process is halted if the
       journal entry is marked as locked.

    Parameters
    ----------
    instance : TransactionModel
        The `TransactionModel` instance that is about to be saved.
    kwargs : dict
        Additional keyword arguments, such as the optional `bypass_account_state`.

    Raises
    ------
    TransactionModelValidationError
        Raised in the following scenarios:
        - **Account Transactionality Failure**:
          When `bypass_account_state` is `False` or not provided, and the
          associated account (`instance.account`) cannot process transactions.
          The exception contains a message identifying the account.

        - **Locked Journal Entry**:
          When the associated journal entry (`instance.journal_entry`) is locked,
          preventing modification of any related transactions. The error message
          describes the locked journal entry constraint.
    """
    bypass_account_state = kwargs.get('bypass_account_state', False)

    if instance.account_id and instance.account.is_root_account():
        raise TransactionModelValidationError(
            message=_('Transactions cannot be linked to root accounts.')
        )

    if all([
        not bypass_account_state,
        not instance.account.can_transact()
    ]):
        raise TransactionModelValidationError(
            message=_(f'Cannot create or modify transactions on account model {instance.account}.')
        )
    if instance.journal_entry.is_locked():
        raise TransactionModelValidationError(
            message=_('Cannot modify transactions on locked journal entries.')
        )


pre_save.connect(transactionmodel_presave, sender=TransactionModel)
