"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

This module provides core functionality for handling data import jobs and staged transactions in the `Django Ledger`
application. It introduces two primary models to facilitate the import and processing of transactions:

1. `ImportJobModel` - Represents jobs that handle financial data import tasks.
2. `StagedTransactionModel` - Represents individual transactions, including those that are staged for review, mapping,
or further processing.

"""

from decimal import Decimal
from typing import Optional, Set, Dict, List
from uuid import uuid4, UUID

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Count, Sum, Case, When, F, Value, DecimalField, BooleanField, Manager, QuerySet
from django.db.models.functions import Coalesce
from django.db.models.signals import pre_save
from django.utils.translation import gettext_lazy as _

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT
from django_ledger.models import JournalEntryModel
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.utils import lazy_loader


class ImportJobModelValidationError(ValidationError):
    pass


class ImportJobModelQuerySet(QuerySet):
    pass


class ImportJobModelManager(Manager):
    """
    Manages queryset operations related to import jobs.

    This manager provides custom queryset handling for import job models, including
    annotations for custom fields like transaction counts, user-specific filters,
    and entity-specific filters. It is integrated with the ImportJobModel, designed
    to support complex query requirements with field annotations and related object
    optimizations for performance efficiency.

    """

    def get_queryset(self):
        """
        Generates a QuerySet with annotated data for ImportJobModel.

        This method constructs a custom QuerySet for ImportJobModel with multiple
        annotations and related fields. It includes counts for specific transaction
        states, calculates pending transactions, and checks for completion status
        of the import job. The QuerySet uses annotations and filters to derive
        various properties required for processing.

        Returns
        -------
        QuerySet
            A QuerySet with additional annotations:
            - _entity_uuid : UUID of the entity associated with the ledger model.
            - _entity_slug : Slug of the entity associated with the ledger model.
            - txs_count : Integer count of non-root transactions.
            - txs_mapped_count : Integer count of mapped transactions based on specific
              conditions.
            - txs_pending : Integer count of pending transactions, calculated as
              txs_count - txs_mapped_count.
            - is_complete : Boolean value indicating if the import job is complete
              (no pending transactions or total count is zero).
        """
        qs = ImportJobModelQuerySet(self.model, using=self._db)
        return qs.annotate(
            _entity_uuid=F('ledger_model__entity__uuid'),
            _entity_slug=F('ledger_model__entity__slug'),
            txs_count=Count('stagedtransactionmodel',
                            filter=Q(stagedtransactionmodel__parent__isnull=False)),
            txs_mapped_count=Count(
                'stagedtransactionmodel__account_model_id',
                filter=Q(stagedtransactionmodel__parent__isnull=False) |
                       Q(stagedtransactionmodel__parent__parent__isnull=False)

            ),
        ).annotate(
            txs_pending=F('txs_count') - F('txs_mapped_count')
        ).annotate(
            is_complete=Case(
                When(txs_count__exact=0, then=False),
                When(txs_pending__exact=0, then=True),
                default=False,
                output_field=BooleanField()
            ),
        ).select_related(
            'bank_account_model',
            'bank_account_model__account_model',
            'ledger_model'
        )

    def for_user(self, user_model):
        """
        Filters the queryset based on the user's permissions for accessing the data
        related to bank accounts and entities they manage or administer.

        This method first retrieves the default queryset. If the user is a superuser,
        the query will return the full queryset without any filters. Otherwise, the
        query will be limited to the entities that the user either administers or is
        listed as a manager for.

        Parameters
        ----------
        user_model : User
            The user model instance whose permissions determine the filtering of the queryset.

        Returns
        -------
        QuerySet
            A filtered queryset based on the user's role and associated permissions.
        """
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
    """
    Abstract model for managing import jobs within a financial system.

    This abstract model serves as a foundational base for managing import jobs involving
    bank accounts and ledger models. It provides functionalities such as linking to an
    associated bank account and ledger model, determining completion status of the
    import job, and properties for UUID and slug identifiers. Additionally, helper
    methods are provided for configuration and deletion confirmation.

    Attributes
    ----------
    uuid : UUID
        Unique identifier for the import job instance.
    description : str
        Descriptive label or description for the import job.
    bank_account_model : BankAccountModel
        Foreign key linking the import job to a bank account model.
    ledger_model : LedgerModel or None
        One-to-one field linking the import job to a ledger model. Can be null or blank.
    completed : bool
        Indicates whether the import job has been completed.
    objects : ImportJobModelManager
        Manager for handling query operations and model lifecycle.
    """
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    description = models.CharField(max_length=200, verbose_name=_('Description'))
    bank_account_model = models.ForeignKey('django_ledger.BankAccountModel',
                                           on_delete=models.CASCADE,
                                           verbose_name=_('Associated Bank Account Model'))
    ledger_model = models.OneToOneField('django_ledger.LedgerModel',
                                        editable=False,
                                        on_delete=models.CASCADE,
                                        verbose_name=_('Ledger Model'),
                                        null=True,
                                        blank=True)
    completed = models.BooleanField(default=False, verbose_name=_('Import Job Completed'))
    objects = ImportJobModelManager()

    class Meta:
        abstract = True
        verbose_name = _('Import Job Model')
        indexes = [
            models.Index(fields=['bank_account_model']),
            models.Index(fields=['ledger_model']),
            models.Index(fields=['completed']),
        ]

    @property
    def entity_uuid(self) -> UUID:
        """
        Get the UUID of the entity associated with the ledger model.

        This property retrieves the UUID of the entity. If the `_entity_uuid`
        attribute exists, it is returned. Otherwise, the UUID is fetched
        from the `entity_model_id` attribute of the `ledger_model` instance.

        Returns
        -------
        str
            The UUID of the entity as a string.
        """
        try:
            return getattr(self, '_entity_uuid')
        except AttributeError:
            pass
        return self.ledger_model.entity_model_id

    @property
    def entity_slug(self) -> str:
        """
        Returns the slug identifier for the entity associated with the current instance.

        The entity slug is a unique string that represents the associated entity in a
        human-readable format. If the `_entity_slug` property is explicitly set, it is
        returned. Otherwise, the slug associated with the `entity_model` within the
        `ledger_model` is used as the default value.


        Returns
        -------
        str
            The slug identifier related to the entity.
        """
        try:
            return getattr(self, '_entity_slug')
        except AttributeError:
            pass
        return self.ledger_model.entity_model.slug

    def is_configured(self):
        """
        Checks if the configuration for the instance is complete.

        This method verifies whether the necessary attributes for ledger model ID
        and bank account model ID are set. Only when both attributes are
        non-None, the configuration is considered complete.

        Returns
        -------
        bool
            True if both `ledger_model_id` and `bank_account_model_id` attributes
            are set (not None), otherwise False.
        """
        return all([
            self.ledger_model_id is not None,
            self.bank_account_model_id is not None
        ])

    def configure(self, commit: bool = True):
        """
        Configures the ledger model if not already configured and optionally commits the changes.

        This method checks if the ledger model is configured, and if not, it creates a new ledger
        based on the associated bank account model's entity model. Additionally, it can commit
        the changes to update the database based on the given parameter.

        Parameters
        ----------
        commit : bool, optional
            Determines whether to persist the changes to the database. Defaults to `True`.
        """
        if not self.is_configured():
            if self.ledger_model_id is None:
                self.ledger_model = self.bank_account_model.entity_model.create_ledger(
                    name=self.description
                )
            if commit:
                self.save(
                    update_fields=[
                        'ledger_model'
                    ])

    def get_delete_message(self) -> str:
        return _(f'Are you sure you want to delete Import Job {self.description}?')


class StagedTransactionModelQuerySet(QuerySet):
    """
    Represents a custom QuerySet for handling staged transaction models.

    This class extends the standard Django QuerySet to add custom filtering methods
    for staged transaction models. These methods help in querying the data based
    on certain conditions specific to the staged transaction model's state or
    relationships.
    """

    def is_pending(self):
        """
        Determines if there are any pending transactions.

        This method filters the objects in the queryset to determine whether there
        are any transactions that are pending (i.e., have a null transaction_model).
        Pending transactions are identified by checking if the `transaction_model` is
        null for any of the objects in the queryset.

        Returns
        -------
        QuerySet
            A QuerySet containing objects with a null `transaction_model`.

        """
        return self.filter(transaction_model__isnull=True)

    def is_imported(self):
        """
        Filter method to determine if the objects in a queryset have been linked with a
        related transaction model. This function checks whether the `transaction_model`
        field in the related objects is non-null.

        Returns
        -------
        QuerySet
            A filtered queryset containing only objects where the `transaction_model`
            is not null.
        """
        return self.filter(transaction_model__isnull=False)

    def is_parent(self):
        """
        Determines whether the current queryset refers to parent objects based on a
        null check for the `parent_id` field.

        This method applies a filter to the queryset and restricts it to objects
        where the `parent_id` is null. It is often used in hierarchical or
        parent-child data structures to fetch only parent items in the structure.

        Returns
        -------
        QuerySet
            A filtered queryset containing only the objects with `parent_id` set
            to null. The type of the queryset depends on the model class used
            when invoking this method.
        """
        return self.filter(parent_id__isnull=True)

    def is_ready_to_import(self):
        """
        Checks whether items are ready to be imported by applying a filter.

        This function filters elements based on the `ready_to_import` attribute.
        It is typically used to identify and retrieve items marked as ready for
        further processing or importing.

        Returns
        -------
        QuerySet
            A QuerySet of elements that satisfy the `ready_to_import` condition.
        """
        return self.filter(ready_to_import=True)


class StagedTransactionModelManager(Manager):

    def get_queryset(self):
        """
        Fetch and annotate the queryset for staged transaction models to include additional
        related fields and calculated annotations for further processing and sorting.

        The method constructs a queryset with various related fields selected and annotated
        for convenience. It includes fields for related account models, units, transactions,
        journal entries, and import jobs. Annotations are added to calculate properties such
        as the number of child transactions, the total amount split, and whether the transaction
        is ready to import or can be split into journal entries.

        Returns
        -------
        QuerySet
            A Django QuerySet preconfigured with selected related fields and annotations
            for staged transaction models.
        """
        qs = StagedTransactionModelQuerySet(self.model, using=self._db)
        return qs.select_related(
            'account_model',
            'unit_model',
            'transaction_model',
            'transaction_model__journal_entry',
            'transaction_model__account',

            'import_job',
            'import_job__bank_account_model__account_model',

            # selecting parent data....
            'parent',
            'parent__account_model',
            'parent__unit_model',
        ).annotate(
            entity_slug=F('import_job__bank_account_model__entity_model__slug'),
            entity_unit=F('transaction_model__journal_entry__entity_unit__name'),
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


class StagedTransactionModelAbstract(CreateUpdateMixIn):
    """
    Represents an abstract model for staged transactions in a financial application.

    This abstract class is designed to handle and manage staged transactions that may be
    split into multiple child transactions for financial processing purposes. It includes
    various attributes and methods to validate, process, and structure financial data for
    import and transaction management. The model supports hierarchical relationships,
    role mapping, unit handling, and other important functionalities required for staged
    transactions.

    Attributes
    ----------
    uuid : UUIDField
        The unique identifier for the transaction.
    parent : ForeignKey
        Reference to the parent transaction if this is a child split transaction.
    import_job : ForeignKey
        Reference to the related import job that this staged transaction is part of.
    fit_id : CharField
        Identifier related to the financial institution transaction (FIT ID).
    date_posted : DateField
        The date on which the transaction was posted.
    bundle_split : BooleanField
        Indicates whether the transaction's split children are bundled into one record.
    activity : CharField
        Proposed activity for the staged transaction (e.g., spending, income categorization).
    amount : DecimalField
        The transaction amount, representing the value of the main transaction.
    amount_split : DecimalField
        The split amount for children when the transaction is split.
    name : CharField
        The name or title for the transaction description.
    memo : CharField
        Additional information or notes attached to the transaction.
    account_model : ForeignKey
        The related account model this transaction is associated with.
    unit_model : ForeignKey
        The unit model or entity associated with this transaction for accounting purposes.
    transaction_model : OneToOneField
        The actual transaction model associated with this staged transaction post-import.
    objects : Manager
        Custom manager for handling queries related to `StagedTransactionModel`.
    """
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

    objects = StagedTransactionModelManager()

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
        """
        Converts a commit dictionary to a list of dictionaries containing
        transactional data. The method processes the transaction's amount,
        determines its type (DEBIT or CREDIT), and bundles relevant information
        from the current object's attributes.

        Parameters
        ----------
        split_amount : Optional[Decimal], optional
            A specific amount to override the transaction's default amount
            (`self.amount`). If not provided, `self.amount` will be used.

        Returns
        -------
        List[Dict]
            A list containing a single dictionary with the following keys:
            - 'account': The account associated with the transaction,
              derived from `self.import_job.bank_account_model.account_model`.
            - 'amount': The absolute value of the transaction amount.
            - 'tx_type': The type of transaction, either DEBIT if the amount
              is positive or CREDIT if negative.
            - 'description': A descriptor for the transaction, taken from
              `self.name`.
            - 'staged_tx_model': A reference to the current object, representing
              the staged transaction model.
        """
        amt = split_amount if split_amount else self.amount
        return [{
            'account': self.import_job.bank_account_model.account_model,
            'amount': abs(amt),
            'tx_type': DEBIT if not amt < 0.00 else CREDIT,
            'description': self.name,
            'staged_tx_model': self
        }]

    def to_commit_dict(self) -> List[Dict]:
        """
        Converts the current transaction or its children into a list of commit dictionaries.

        Summarizes information about the transaction or its split children into
        dictionaries containing essential details for committing the transaction.
        Depending on whether the current transaction has child transactions, it processes
        either the child transactions or itself to construct the dictionaries.

        Returns
        -------
        List[Dict]
            A list of dictionaries, each representing a transaction with fields such as
            account, absolute amount, staged amount, unit model, transaction type, description,
            and the corresponding staged transaction model.
        """
        if self.has_children():
            children_qs = self.split_transaction_set.all().prefetch_related(
                'split_transaction_set',
                'split_transaction_set__account_model',
                'split_transaction_set__unit_model'
            )
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
        """
        Generates a list of commit dictionaries or splits commit dictionaries based
        on staged amounts if specified.

        Parameters
        ----------
        split_txs : bool, optional
            A flag indicating whether to split transactions by their staged amounts.
            If True, the function will generate a split for each staged amount in
            the commit dictionary. Defaults to False.

        Returns
        -------
        list
            A list representing the commit data. If `split_txs` is True, each entry
            contains pairs of split commit dictionaries and their corresponding
            data. Otherwise, it contains combined commit dictionary data.
        """
        if split_txs:
            to_commit = self.to_commit_dict()
            return [
                [
                    self.from_commit_dict(split_amount=to_split['amount_staged'])[0], to_split
                ] for to_split in
                to_commit
            ]
        return [self.from_commit_dict() + self.to_commit_dict()]

    def get_amount(self) -> Decimal:
        """
        Returns the appropriate amount based on the object's state.

        This method determines the amount to be returned based on whether the object
        is classified as a "children" or not. If the `is_children` method returns True,
        it returns the value of `amount_split`. Otherwise, it returns the value of the
        `amount` attribute.

        Returns
        -------
        Decimal
            The calculated amount based on the object's state.
        """
        if self.is_children():
            return self.amount_split
        return self.amount

    def is_imported(self) -> bool:
        """
        Determines if the necessary models have been imported for the system to function
        properly. This method checks whether both `account_model_id` and
        `transaction_model_id` are set.

        Returns
        -------
        bool
            True if both `account_model_id` and `transaction_model_id` are not None,
            indicating that the models have been successfully imported. False otherwise.
        """
        return all([
            self.account_model_id is not None,
            self.transaction_model_id is not None,
        ])

    def is_pending(self) -> bool:
        """
        Determine if the transaction is pending.

        A transaction is considered pending if it has not been assigned a
        `transaction_model_id`. This function checks the attribute and returns
        a boolean indicating the status.

        Returns
        -------
        bool
            True if the transaction is pending (i.e., `transaction_model_id`
            is None), False otherwise.
        """
        return self.transaction_model_id is None

    def is_mapped(self) -> bool:
        """
        Determines if an account model is mapped.

        This method checks whether the `account_model_id` is assigned a value,
        indicating that the account model has been mapped. It returns a boolean
        result based on the presence of the `account_model_id`.

        Returns
        -------
        bool
            True if `account_model_id` is not None, indicating the account
            model is mapped. False otherwise.
        """
        return self.account_model_id is not None

    def is_single(self) -> bool:
        """
        Checks whether the current instance represents a single entry.

        This method determines if the current object qualifies as a single entry
        by ensuring that it both does not have children and is not considered a
        child of any other entry. The result is a boolean value indicating
        whether the entry meets these criteria.

        Returns
        -------
        bool
            True if the entry is a single, standalone entry; False otherwise.
        """
        return all([
            not self.is_children(),
            not self.has_children()
        ])

    def is_children(self) -> bool:
        """
        Determines if the current instance qualifies as a child entity based on the existence of a parent ID.

        Checks whether the current object is associated with a parent by verifying the presence of `parent_id`.
        The method returns `True` if the `parent_id` attribute is not `None`, indicating that the object is indeed a child.

        Returns
        -------
        bool
            True if the object has a valid `parent_id`, indicating it is a child entity;
            False otherwise.
        """
        return all([
            self.parent_id is not None,
        ])

    def has_activity(self) -> bool:
        """
        Determine if an activity is present.

        This method checks whether the `activity` attribute is assigned a value
        or not. If a value is set, it indicates that there is an associated
        activity. Otherwise, no activity is present.

        Returns
        -------
        bool
            True if the `activity` attribute is not None, indicating the
            presence of an activity. False otherwise.
        """
        return self.activity is not None

    def has_children(self) -> bool:
        """
        Determines if the current instance has children.

        The method checks the state of the instance to determine whether
        it is in the process of adding. If so, it directly returns False,
        signifying no children are present at that moment. Otherwise,
        it evaluates the `children_count` attribute to decide.

        Returns
        -------
        bool
            True if the instance has children and is not in the process of
            adding; otherwise, False.
        """
        if self._state.adding:
            return False
        return getattr(self, 'children_count') > 0

    def can_split(self) -> bool:
        """
        Determines if the current object can be split based on its child status.

        This method checks whether the object does not have any children and, as
        a result, is capable of being split.

        Returns
        -------
        bool
            `True` if the object has no children and can be split, otherwise
            `False`.
        """
        return not self.is_children()

    def can_have_unit(self) -> bool:
        """
        Check if the entity can have a unit.

        This method evaluates the conditions under which an entity may have a
        unit assigned. It considers several factors including the state of
        the entity, whether it has children, if all children are mapped, and
        its relationship to its parent entity.

        Returns
        -------
        bool
            A boolean value indicating whether the entity can have a unit.
            Returns `True` if the conditions are satisfied, otherwise `False`.
        """
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

        return False

    def can_have_account(self) -> bool:
        """
        Determines if an account can be created based on the current state.

        This method assesses whether an account can be created for an entity
        by checking if the entity has any children. The account creation is
        prohibited if the entity has children and allowed otherwise.

        Returns
        -------
        bool
            True if the entity can have an account, False otherwise.
        """
        return not self.has_children()

    def can_import(self, as_split: bool = False) -> bool:
        """
        Determines whether the object is ready for importing data and can optionally
        be split into "je" (journal entries) for import if applicable.

        This method evaluates the readiness of the object for importing based on
        its attributes and conditions. It first checks if the object is marked as
        ready for import. If the object supports splitting into journal entries
        and the `as_split` argument is True, the method considers it eligible for
        import as split entries. If neither of the above conditions are met, it
        checks whether the role mapping is valid without raising exceptions and
        returns the result.

        Parameters
        ----------
        as_split : bool, optional
            Specifies if the object should be checked for readiness to be split
            into "je" (journal entries) for import. Defaults to False.

        Returns
        -------
        bool
            True if the object is ready to import (optionally as split entries),
            otherwise False.
        """
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
        """
        Adds a specified number of split transactions to the staged transaction.

        The method checks whether the staged transaction can be split and ensures it
        has no children before proceeding. If requested, it raises an exception if a split
        transaction is not allowed. New split transactions are created and validated before
        optionally committing them to the database.

        Parameters
        ----------
        raise_exception : bool
            Determines if an exception should be raised when splitting is not allowed.
            Default is True.
        commit : bool
            Indicates whether to commit the newly created split transactions to the
            database. Default is True.
        n : int, optional
            The number of split transactions to create. If the staged transaction has
            no children, one additional split transaction is created. Default is 1.

        Returns
        -------
        list of StagedTransactionModel
            List of newly created staged transactions in the split.
        """
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
        """
        Indicates whether the total amount is distributed as per the split rules.

        Returns
        -------
        bool
            True if the `amount` attribute equals the `total_amount_split` attribute,
            indicating the total amount is split correctly; False otherwise.
        """
        return self.amount == getattr(self, 'total_amount_split')

    def are_all_children_mapped(self) -> bool:
        """
        Determines whether all children have been mapped.

        This method compares the total number of children with the number
        of mapped children to check whether all children have been mapped.

        Returns
        -------
        bool
            True if the number of children equals the number of mapped children,
            otherwise False.
        """
        return getattr(self, 'children_count') == getattr(self, 'children_mapped_count')

    def get_import_role_set(self) -> Set[str]:
        """
        Retrieves the set of roles associated with import.

        This method determines the role(s) based on the current instance's state and
        its associated transactions. If the instance is single and mapped, the role
        directly tied to its account model is returned. If the instance has child
        split transactions and all of them are mapped, the roles associated with
        each transaction's account model, excluding a specific type of role, are
        aggregated and returned as a set.

        Returns
        -------
        Set[str]
            A set of roles derived from the account model(s) relating to the
            instance or its child transactions. Returns empty set if no roles
            can be determined.
        """
        if self.is_single() and self.is_mapped():
            return {self.account_model.role}
        if self.has_children():
            split_txs_qs = self.split_transaction_set.all()
            if all([txs.is_mapped() for txs in split_txs_qs]):
                return set([txs.account_model.role for txs in split_txs_qs if txs.account_model.role != ASSET_CA_CASH])
        return set()

    def get_prospect_je_activity_try(self, raise_exception: bool = True, force_update: bool = False) -> Optional[str]:
        """
        Retrieve or attempt to fetch the journal entry activity for the current prospect object.

        The method determines whether the activity should be updated or fetched based on the
        current state. If the `force_update` flag is set to True or required conditions are met,
        it attempts to retrieve the activity from the associated roles of the journal entry.
        The activity is then saved and optionally returned. If an exception occurs during this
        process and `raise_exception` is set to True, the exception is propagated.

        Parameters
        ----------
        raise_exception : bool, optional
            Specifies whether to raise exceptions in case of validation errors.
            Default is True.
        force_update : bool, optional
            Forces the method to fetch and update the activity even if it already exists.
            Default is False.

        Returns
        -------
        Optional[str]
            The journal entry activity if successfully retrieved or updated; otherwise,
            returns the existing activity or None if no activity is present.
        """
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
        """
        Gets the activity of the prospect JE (Journal Entry) in a safe manner.

        This method retrieves the activity of the prospect journal entry (JE). If the
        activity cannot be retrieved, it will return `None` instead of raising an
        exception. It serves as a wrapper for the `get_prospect_je_activity_try`
        method by specifying that exceptions should not be raised during retrieval.

        Returns
        -------
        Optional[str]
            The activity of the prospect journal entry if available, otherwise `None`.
        """
        return self.get_prospect_je_activity_try(raise_exception=False)

    def get_prospect_je_activity_display(self) -> Optional[str]:
        """
        Provides functionality to retrieve and display the prospect journal entry activity
        based on the mapped activity associated with a prospect. The method attempts to
        fetch the journal entry activity safely and returns its display name if available.

        Returns
        -------
        Optional[str]
            The display name of the prospect journal entry activity if it exists,
            otherwise None.
        """
        activity = self.get_prospect_je_activity_try(raise_exception=False)
        if activity is not None:
            JournalEntryModel = lazy_loader.get_journal_entry_model()
            return JournalEntryModel.MAP_ACTIVITIES[activity]

    def is_role_mapping_valid(self, raise_exception: bool = False) -> bool:
        """
        Determines if the role mapping is valid by verifying associated activities.

        The method checks for the presence of an activity linked to the object.
        If no activity is found, it attempts to fetch one. The validity of the
        role mapping is determined by the success of this process.

        Parameters
        ----------
        raise_exception : bool, optional
            Determines whether to raise an exception if validation fails
            (default is False).

        Returns
        -------
        bool
            True if the role mapping is valid, otherwise False.

        Raises
        ------
        ValidationError
            If raise_exception is set to True and the validation process fails.
        """
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
        """
        Migrate transactional data to the ledger model by processing the provided
        transactions and committing them. This process involves using the provided
        parameter to determine transaction splitting and subsequently saving the
        processed transactional data for each entry in the commit dictionary.

        Parameters
        ----------
        split_txs : bool, optional
            A flag that determines whether the transactions should be split into
            multiple entries based on the associated commit data. Defaults to False.

        Notes
        -----
        The method checks if the transactional data can be imported using the
        `can_import` method. If successful, it creates a commit dictionary and
        processes it by committing all transactional data to the ledger model.
        The saved objects are staged with appropriate models to retain the
        transaction state.
        """
        if self.can_import(as_split=split_txs):
            commit_dict = self.commit_dict(split_txs=split_txs)
            import_job = self.import_job
            ledger_model = import_job.ledger_model

            if len(commit_dict) > 0:
                for je_data in commit_dict:
                    unit_model = self.unit_model if not split_txs else commit_dict[0][1]['unit_model']
                    _, _ = ledger_model.commit_txs(
                        je_timestamp=self.date_posted,
                        je_unit_model=unit_model,
                        je_txs=je_data,
                        je_desc=self.memo,
                        je_posted=False,
                        force_je_retrieval=False
                    )
                    staged_to_save = [i['staged_tx_model'] for i in je_data]
                    for i in staged_to_save:
                        i.save(
                            update_fields=['transaction_model', 'updated']
                        )

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

    class Meta(ImportJobModelAbstract.Meta):
        abstract = False


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

    class Meta(StagedTransactionModelAbstract.Meta):
        abstract = False
