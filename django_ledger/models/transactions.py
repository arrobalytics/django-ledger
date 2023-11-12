"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

The TransactionModel is the lowest accounting level where the financial information is recorded on the books.
Every transaction which has an financial implication must be recorded as part of a JournalEntryModel, which in turn
encapsulates a collection of TransactionModels. Transaction models cannot exist without being part of a validated
JournalEntryModel. Orphan TransactionModels are not allowed, and this is enforced by the database.

A transaction by definition must perform a CREDIT or a DEBIT to the underlying AccountModel. The IOMixIn plays a crucial
role in the production of financial statements and sets its foundation in the TransactionModel API to effective query
amd aggregate transactions at the Database layer without the need of pulling all TransactionModels into memory for the
production of financial statements.
"""
from datetime import datetime, date
from typing import List, Union, Optional
from uuid import uuid4, UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _

from django_ledger.io import validate_io_date
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
    A custom defined EntityUnitModel Queryset.
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
            to_date = validate_io_date(to_date)

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
            from_date = validate_io_date(from_date)

        if isinstance(from_date, date):
            return self.filter(journal_entry__timestamp__date__gte=from_date)

        return self.filter(journal_entry__timestamp__gte=from_date)

    def not_closing_entry(self):
        return self.filter(journal_entry__is_closing_entry=False)

    def is_closing_entry(self):
        return self.filter(journal_entry__is_closing_entry=True)


class TransactionModelAdmin(models.Manager):

    def for_user(self, user_model) -> TransactionModelQuerySet:
        """
        Fetches a QuerySet of TransactionModels that the UserModel as access to. For convenience, the AccountModel
        information is selected, since much of the operations associated with transactions will involve information
        from the AccountModel. For example, the AccountModel balance type plays a crucial role in the production of
        financial statements.

        May include TransactionModels from multiple Entities.

        The user has access to transactions if:
            1. Is listed as Manager of Entity.
            2. Is the Admin of the Entity.

        Parameters
        ----------
        user_model
            Logged in and authenticated django UserModel instance.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
        """
        qs = self.get_queryset()
        return qs.filter(
            Q(journal_entry__ledger__entity__admin=user_model) |
            Q(journal_entry__ledger__entity__managers__in=[user_model])
        )

    def for_entity(self,
                   entity_slug: Union[EntityModel, str, UUID],
                   user_model: Optional[UserModel] = None,
                   ) -> TransactionModelQuerySet:
        """
        Fetches a QuerySet of TransactionModels associated with the specified
        EntityModel. For security if UserModel is provided, will make sure the user_model provided is either the admin
        or the manager of the entity.

        Parameters
        ----------
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model: Optional Django UserModel
            Optional logged in and authenticated Django UserModel instance to match against Entity Admin or Managers.
            Will make sure the authenticated user has access to the EntityModel transactions.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
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
        Fetches a QuerySet of TransactionModels that the UserModel as access to and are associated with a specific
        LedgerModel instance.

        Parameters
        ----------
        user_model
            Optional logged in and authenticated django UserModel instance to validate against managers and admin.
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        ledger_model: LedgerModel or UUID
            The LedgerModel or LedgerModel UUID associated with the TransactionModel to be queried.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
        """
        qs = self.for_entity(user_model=user_model, entity_slug=entity_slug)
        if isinstance(ledger_model, LedgerModel):
            return qs.filter(journal_entry__ledger=ledger_model)
        elif isinstance(ledger_model, str) or isinstance(ledger_model, UUID):
            return qs.filter(journal_entry__ledger__uuid__exact=ledger_model)

    def for_unit(self,
                 entity_slug: Union[EntityModel, str],
                 unit_slug: str = Union[EntityUnitModel, str],
                 user_model: Optional[UserModel] = None):
        """
        Fetches a QuerySet of TransactionModels that the UserModel as access to and are associated with a specific
        EntityUnitModel instance.

        Parameters
        ----------
        user_model
            Optional logged in and authenticated django UserModel instance to validate against managers and admin.
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        unit_slug: EntityUnitModel or EntityUnitModel UUID.
            The EntityUnitModel or EntityUnitModel UUID associated with the TransactionModel to be queried.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
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
        Fetches a QuerySet of TransactionModels that the UserModel as access to and are associated with a specific
        LedgerModel AND JournalEntryModel instance.

        Parameters
        ----------
        user_model: UserModel
            Optional logged in and authenticated django UserModel instance to validate against managers and admin.
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        ledger_model: LedgerModel or str or UUID
            The LedgerModel or LedgerModel UUID associated with the TransactionModel to be queried.
        je_model: JournalEntryModel or str or UUID
            The JournalEntryModel or JournalEntryModel UUID associated with the TransactionModel to be queried.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
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
        Fetches a QuerySet of TransactionModels that the UserModel as access to and are associated with a specific
        BillModel instance.

        Parameters
        ----------
        user_model
            Logged in and authenticated django UserModel instance.
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        bill_model: BillModel or str or UUID
            The BillModel or BillModel UUID associated with the TransactionModel to be queried.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
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
        Fetches a QuerySet of TransactionModels that the UserModel as access to and are associated with a specific
        InvoiceModel instance.

        Parameters
        ----------
        user_model
            Logged in and authenticated django UserModel instance.
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        invoice_model: InvoiceModel or str or UUID
            The InvoiceModel or InvoiceModel UUID associated with the TransactionModel to be queried.

        Returns
        -------
        TransactionModelQuerySet
            Returns a TransactionModelQuerySet with applied filters.
        """
        qs = self.for_entity(
            user_model=user_model,
            entity_slug=entity_slug)
        if isinstance(invoice_model, InvoiceModel):
            return qs.filter(journal_entry__ledger__invoicemodel=invoice_model)
        return qs.filter(journal_entry__ledger__invoicemodel__uuid__exact=invoice_model)


class TransactionModelAbstract(CreateUpdateMixIn):
    """
    This is the main abstract class which the BillModel database will inherit from.
    The BillModel inherits functionality from the following MixIns:

        1. :func:`CreateUpdateMixIn <django_ledger.models.mixins.CreateUpdateMixIn>`

    Attributes
    ----------
    uuid : UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().
    tx_type: str
        Transaction type as a String, representing a CREDIT or a DEBIT to the AccountModel associated with the
        TransactionModel instance.
    journal_entry: JournalEntryModel
        The JournalEntryModel associated with the TransactionModel instance.
    account: AccountModel
        The AccountModel associated with the TransactionModel instance.
    amount: Decimal
        The monetary amount of the transaction instance, represented by the python Decimal field.
        Must be greater than zero.
    description: str
        A TransactionModel description. Maximum length is 100.
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
    objects = TransactionModelAdmin.from_queryset(queryset_class=TransactionModelQuerySet)()

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
        # pylint: disable=no-member
        return '{x1}-{x2}/{x5}: {x3}/{x4}'.format(x1=self.account.code,
                                                  x2=self.account.name,
                                                  x3=self.amount,
                                                  x4=self.tx_type,
                                                  x5=self.account.balance_type)

    def clean(self):
        if self.account.is_root_account():
            raise TransactionModelValidationError(
                message=_('Cannot transact on root accounts')
            )


class TransactionModel(TransactionModelAbstract):
    """
    Base Transaction Model From Abstract.
    """
