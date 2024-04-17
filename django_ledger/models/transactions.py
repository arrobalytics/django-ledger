"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

The TransactionModel is the lowest accounting level where financial information is recorded. Every transaction with a
financial implication must be part of a JournalEntryModel, which encapsulates a collection of TransactionModels.
Transaction models cannot exist without being part of a validated JournalEntryModel. Orphan TransactionModels are not
allowed, and this is enforced by the database.

A transaction must perform a CREDIT or a DEBIT to the underlying AccountModel. The IOMixIn is crucial for the
production of financial statements and sets its foundation in the TransactionModel API. It allows for effective
querying and aggregating transactions at the Database layer without pulling all TransactionModels into memory.
This approach streamlines the production of financial statements. The IOMixIn in the TransactionModel API is essential
for efficient and effective financial statement generation.
"""
from datetime import datetime, date
from typing import List, Union, Optional
from uuid import uuid4, UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, QuerySet
from django.db.models.signals import pre_save
from django.utils.translation import gettext_lazy as _

from django_ledger.io.io_core import validate_io_timestamp
from django_ledger.models.accounts import AccountModel
from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.unit import EntityUnitModel
from django_ledger.models.utils import lazy_loader

UserModel = get_user_model()


class TransactionModelValidationError(ValidationError):
    pass


class TransactionModelQuerySet(QuerySet):
    """
    A custom QuerySet class for TransactionModels implementing methods to effectively and safely read
    TransactionModels from the database.

    Methods
    -------
    posted() -> TransactionModelQuerySet:
        Fetches a QuerySet of posted transactions only.

    for_accounts(account_list: List[str or AccountModel]) -> TransactionModelQuerySet:
        Fetches a QuerySet of TransactionModels which AccountModel has a specific role.

    for_roles(role_list: Union[str, List[str]]) -> TransactionModelQuerySet:
        Fetches a QuerySet of TransactionModels which AccountModel has a specific role.

    for_unit(unit_slug: Union[str, EntityUnitModel]) -> TransactionModelQuerySet:
        Fetches a QuerySet of TransactionModels associated with a specific EntityUnitModel.

    for_activity(activity_list: Union[str, List[str]]) -> TransactionModelQuerySet:
        Fetches a QuerySet of TransactionModels associated with a specific activity or list of activities.

    to_date(to_date: Union[str, date, datetime]) -> TransactionModelQuerySet:
        Fetches a QuerySet of TransactionModels associated with a maximum date or timestamp filter.

    from_date(from_date: Union[str, date, datetime]) -> TransactionModelQuerySet:
        Fetches a QuerySet of TransactionModels associated with a minimum date or timestamp filter.

    not_closing_entry() -> TransactionModelQuerySet:
        Fetches a QuerySet of TransactionModels that are not part of a closing entry.

    is_closing_entry() -> TransactionModelQuerySet:
        Fetches a QuerySet of TransactionModels that are part of a closing entry.
    """

    def posted(self) -> QuerySet:
        """
        Fetches a QuerySet of posted transactions only.
        Posted transactions are must meet the following criteria:
            * Be bart of a *posted* JournalEntryModel.
            * The associated JournalEntryModel must be part of a *posted* LedgerModel.

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet with applied filters.
        """
        return self.filter(
            Q(journal_entry__posted=True) &
            Q(journal_entry__ledger__posted=True)
        )

    def for_accounts(self, account_list: List[str or AccountModel]):
        """
        Fetches a QuerySet of TransactionModels which AccountModel has a specific role.

        Parameters
        ----------
        account_list: list
            A string or list of strings representing the roles to be used as filter.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
        """
        if len(account_list) > 0 and isinstance(account_list[0], str):
            return self.filter(account__code__in=account_list)
        return self.filter(account__in=account_list)

    def for_roles(self, role_list: Union[str, List[str]]):
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

    def for_unit(self, unit_slug: Union[str, EntityUnitModel]):
        """
        Fetches a QuerySet of TransactionModels associated with a specific EntityUnitModel.

        Parameters
        ----------
        unit_slug: str or EntityUnitModel
            A string representing the unit slug used to filter the QuerySet.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
        """
        if isinstance(unit_slug, EntityUnitModel):
            return self.filter(journal_entry__ledger__unit=unit_slug)
        return self.filter(journal_entry__ledger__unit__slug__exact=unit_slug)

    def for_activity(self, activity_list: Union[str, List[str]]):
        """
        Fetches a QuerySet of TransactionModels associated with a specific activity or list of activities.

        Parameters
        ----------
        activity_list: str or list
            A string or list of strings representing the activity or activities used to filter the QuerySet.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
        """
        if isinstance(activity_list, str):
            return self.filter(journal_entry__activity__in=[activity_list])
        return self.filter(journal_entry__activity__in=activity_list)

    def to_date(self, to_date: Union[str, date, datetime]):
        """
        Fetches a QuerySet of TransactionModels associated with a maximum date or timestamp filter.
        May pass aware or naive date or timestamps. If naive is passed, it is assumed to be in localtime based
        on Django Settings.

        Parameters
        ----------
        to_date: str or date or datetime
            A string, date or datetime  representing the maximum point in time used to filter the QuerySet.
            If date is used, dates are inclusive. (i.e 12/20/2022 will also include the 20th day).

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
        """

        if isinstance(to_date, str):
            to_date = validate_io_timestamp(to_date)

        if isinstance(to_date, date):
            return self.filter(journal_entry__timestamp__date__lte=to_date)
        return self.filter(journal_entry__timestamp__lte=to_date)

    def from_date(self, from_date: Union[str, date, datetime]):
        """
        Fetches a QuerySet of TransactionModels associated with a minimum date or timestamp filter.
        May pass aware or naive date or timestamps. If naive is passed, it is assumed to be in localtime based
        on Django Settings.

        Parameters
        ----------
        from_date: str or date or datetime
            A string, date or datetime  representing the minimum point in time used to filter the QuerySet.
            If date is used, dates are inclusive. (i.e 12/20/2022 will also include the 20th day).

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
        """
        if isinstance(from_date, str):
            from_date = validate_io_timestamp(from_date)

        if isinstance(from_date, date):
            return self.filter(journal_entry__timestamp__date__gte=from_date)

        return self.filter(journal_entry__timestamp__gte=from_date)

    def not_closing_entry(self):
        """
        Filter the Transactions based on whether they are closing entries or not.

        Returns:
            QuerySet: A filtered QuerySet of entries where the journal_entry__is_closing_entry field is False.
        """
        return self.filter(journal_entry__is_closing_entry=False)

    def is_closing_entry(self):
        """
        Filter the Transactions based on whether they are closing entries or not.

        Returns:
            QuerySet: A filtered QuerySet of entries where the journal_entry__is_closing_entry field is True.
        """
        return self.filter(journal_entry__is_closing_entry=True)


class TransactionModelAdmin(models.Manager):
    """
    A manager class for the TransactionModel.
    """

    def get_queryset(self) -> TransactionModelQuerySet:
        qs = TransactionModelQuerySet(self.model, using=self._db)
        return qs.select_related(
            'journal_entry',
            'account',
            'account__coa_model',
        )

    def for_user(self, user_model) -> TransactionModelQuerySet:
        """
        Parameters
        ----------
        user_model : User model object
            The user model object representing the user for whom to filter the transactions.

        Returns
        -------
        TransactionModelQuerySet
            A queryset of transaction models filtered based on the user's permissions.

        Raises
        ------
        None

        Description
        -----------
        This method filters the transactions based on the user's permissions.
        If the user is a superuser, all transactions are returned. Otherwise, the transactions are filtered based on
        the user's relationship to the entities associated with the transactions. Specifically, the transactions are
        filtered to include only those where either the user is an admin of the entity associated with the transaction's
        ledger or the user is one of the managers of the entity associated with the transaction's ledger.
        """
        qs = self.get_queryset()
        if user_model.is_superuser:
            return qs
        return qs.filter(
            Q(journal_entry__ledger__entity__admin=user_model) |
            Q(journal_entry__ledger__entity__managers__in=[user_model])
        )

    def for_entity(self,
                   entity_slug: Union[EntityModel, str, UUID],
                   user_model: Optional[UserModel] = None,
                   ) -> TransactionModelQuerySet:
        """
        Parameters
        ----------
        entity_slug : Union[EntityModel, str, UUID]
            The entity slug or ID for which to retrieve transactions.
            Can be an instance of EntityModel, a string representing the slug, or a UUID.
        user_model : Optional[UserModel], optional
            The user model for which to filter transactions.
            If provided, only transactions associated with the specified user will be returned.
            Defaults to None.

        Returns
        -------
        TransactionModelQuerySet
            A QuerySet of TransactionModel instances filtered by the provided parameters.
        """

        if user_model:
            qs = self.for_user(user_model=user_model)
        else:
            qs = self.get_queryset()

        if isinstance(entity_slug, EntityModel):
            return qs.filter(journal_entry__ledger__entity=entity_slug)
        elif isinstance(entity_slug, UUID):
            return qs.filter(journal_entry__ledger__entity_id=entity_slug)
        return qs.filter(journal_entry__ledger__entity__slug__exact=entity_slug)

    def for_ledger(self,
                   entity_slug: Union[EntityModel, str],
                   ledger_model: Union[LedgerModel, UUID],
                   user_model: Optional[UserModel] = None):
        """
        Parameters
        ----------
        entity_slug : Union[EntityModel, str]
            The slug or instance of the entity for which to filter the ledger.
        ledger_model : Union[LedgerModel, UUID]
            The ledger model or UUID of the ledger for which to filter the journal entries.
        user_model : Optional[UserModel], optional
            The user model associated with the entity. Default is None.

        Returns
        -------
        QuerySet
            The filtered QuerySet containing the journal entries for the specified entity and ledger.
        """
        qs = self.for_entity(user_model=user_model, entity_slug=entity_slug)
        if isinstance(ledger_model, UUID):
            return qs.filter(journal_entry__ledger__uuid__exact=ledger_model)
        return qs.filter(journal_entry__ledger=ledger_model)

    def for_unit(self,
                 entity_slug: Union[EntityModel, str],
                 unit_slug: str = Union[EntityUnitModel, str],
                 user_model: Optional[UserModel] = None):
        """
        Returns the queryset filtered for the specified entity unit.

        Parameters
        ----------
        entity_slug : Union[EntityModel, str]
            The entity model or slug used to filter the queryset.
        unit_slug : Union[EntityUnitModel, str]
            The entity unit model or slug used to filter the queryset.
        user_model : Optional[UserModel], optional
            The user model to consider for filtering the queryset, by default None.

        Returns
        -------
        QuerySet
            The filtered queryset based on the specified entity unit.

        Notes
        -----
        - If `unit_slug` is an instance of `EntityUnitModel`, the queryset is filtered using `journal_entry__entity_unit=unit_slug`.
        - If `unit_slug` is a string, the queryset is filtered using `journal_entry__entity_unit__slug__exact=unit_slug`.
        """
        qs = self.for_entity(user_model=user_model, entity_slug=entity_slug)
        if isinstance(unit_slug, EntityUnitModel):
            return qs.filter(journal_entry__entity_unit=unit_slug)
        return qs.filter(journal_entry__entity_unit__slug__exact=unit_slug)

    def for_journal_entry(self,
                          entity_slug: Union[EntityModel, str],
                          ledger_model: Union[LedgerModel, str, UUID],
                          je_model,
                          user_model: Optional[UserModel] = None):
        """
        Parameters
        ----------
        entity_slug : Union[EntityModel, str]
            The entity slug or instance of EntityModel representing the entity for which the journal entry is requested.
        ledger_model : Union[LedgerModel, str, UUID]
            The ledger model or its identifier (str or UUID) representing the ledger for which the journal entry
            is requested.
        je_model : Type[JournalEntryModel]
            The journal entry model or its identifier (str or UUID) representing the journal entry to filter by.
        user_model : Optional[UserModel], default=None
            An optional user model instance representing the user for whom the journal entry is requested.

        Returns
        -------
        QuerySet
            The filtered queryset of journal entries.

        """
        qs = self.for_ledger(user_model=user_model,
                             entity_slug=entity_slug,
                             ledger_model=ledger_model)

        if isinstance(je_model, lazy_loader.get_journal_entry_model()):
            return qs.filter(journal_entry=je_model)
        return qs.filter(journal_entry__uuid__exact=je_model)

    def for_bill(self,
                 user_model,
                 entity_slug: str,
                 bill_model: Union[BillModel, str, UUID]):
        """
        Parameters
        ----------
        user_model : Type
            An instance of user model.
        entity_slug : str
            The slug of the entity.
        bill_model : Union[BillModel, str, UUID]
            An instance of bill model or a string/UUID representing the UUID of the bill model.

        Returns
        -------
        FilterQuerySet
            A filtered queryset based on the user model, entity slug, and bill model.

        """
        qs = self.for_entity(
            user_model=user_model,
            entity_slug=entity_slug)
        if isinstance(bill_model, BillModel):
            return qs.filter(journal_entry__ledger__billmodel=bill_model)
        return qs.filter(journal_entry__ledger__billmodel__uuid__exact=bill_model)

    def for_invoice(self,
                    user_model,
                    entity_slug: str,
                    invoice_model: Union[InvoiceModel, str, UUID]):
        """
        Parameters
        ----------
        user_model : [type]
            The user model used for filtering entities.
        entity_slug : str
            The slug of the entity used for filtering.
        invoice_model : Union[InvoiceModel, str, UUID]
            The invoice model or its identifier used for filtering.

        Returns
        -------
        QuerySet
            The filtered queryset based on the specified parameters.
        """
        qs = self.for_entity(
            user_model=user_model,
            entity_slug=entity_slug)
        if isinstance(invoice_model, InvoiceModel):
            return qs.filter(journal_entry__ledger__invoicemodel=invoice_model)
        return qs.filter(journal_entry__ledger__invoicemodel__uuid__exact=invoice_model)


class TransactionModelAbstract(CreateUpdateMixIn):
    """

    TransactionModelAbstract

    An abstract class that represents a transaction in the ledger system.

    Attributes
    ----------

    - CREDIT: A constant representing a credit transaction.
    - DEBIT: A constant representing a debit transaction.

    - TX_TYPE: A list of tuples representing the transaction type choices.

    - uuid: A UUIDField representing the unique identifier of the transaction.
        This field is automatically generated and is not editable.

    - tx_type: A CharField representing the type of the transaction.
        It has a maximum length of 10 characters and accepts choices from the TX_TYPE list.

    - journal_entry: A ForeignKey representing the journal entry associated with the transaction.
        It references the 'django_ledger.JournalEntryModel' model.

    - account: A ForeignKey representing the account associated with the transaction.
        It references the 'django_ledger.AccountModel' model.

    - amount: A DecimalField representing the amount of the transaction.
        It has a maximum of 2 decimal places and a maximum of 20 digits.
        It defaults to 0.00 and accepts a minimum value of 0.

    - description: A CharField representing the description of the transaction.
        It has a maximum length of 100 characters and is optional.

    - objects: An instance of the TransactionModelAdmin class.

    Methods
    -------

    - clean(): Performs validation on the transaction instance.
        Raises a TransactionModelValidationError if the account is a root account.

    """

    CREDIT = 'credit'
    DEBIT = 'debit'

    TX_TYPE = [
        (CREDIT, _('Credit')),
        (DEBIT, _('Debit'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    tx_type = models.CharField(max_length=10, choices=TX_TYPE, verbose_name=_('Tx Type'))
    journal_entry = models.ForeignKey('django_ledger.JournalEntryModel',
                                      editable=False,
                                      verbose_name=_('Journal Entry'),
                                      help_text=_('Journal Entry to be associated with this transaction.'),
                                      on_delete=models.CASCADE)
    account = models.ForeignKey('django_ledger.AccountModel',
                                verbose_name=_('Account'),
                                help_text=_('Account from Chart of Accounts to be associated with this transaction.'),
                                on_delete=models.PROTECT)
    amount = models.DecimalField(decimal_places=2,
                                 max_digits=20,
                                 default=0.00,
                                 verbose_name=_('Amount'),
                                 help_text=_('Account of the transaction.'),
                                 validators=[MinValueValidator(0)])
    description = models.CharField(max_length=100,
                                   null=True,
                                   blank=True,
                                   verbose_name=_('Tx Description'),
                                   help_text=_('A description to be included with this individual transaction'))

    objects = TransactionModelAdmin()

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
            models.Index(fields=['updated'])
        ]

    def __str__(self):
        return '{x1}-{x2}/{x5}: {x3}/{x4}'.format(x1=self.account.code,
                                                  x2=self.account.name,
                                                  x3=self.amount,
                                                  x4=self.tx_type,
                                                  x5=self.account.balance_type)

    def clean(self):
        if self.account_id and self.account.is_root_account():
            raise TransactionModelValidationError(
                message=_('Cannot transact on root accounts')
            )


class TransactionModel(TransactionModelAbstract):
    """
    Base Transaction Model From Abstract.
    """


def transactionmodel_presave(instance: TransactionModel, **kwargs):
    """
    Parameters
    ----------
    instance : TransactionModel
        The transaction model instance that is being saved.
    kwargs : dict
        Additional keyword arguments.

    Notes
    -----
    This method is called before saving a transaction model instance.
    It performs some checks before allowing the save operation.

    Raises
    ------
    TransactionModelValidationError
        If one of the following conditions is met:
        - `bypass_account_state` is False and the `can_transact` method of the associated account model returns False.
        - The journal entry associated with the transaction is locked.

    """
    bypass_account_state = kwargs.get('bypass_account_state', False)
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
