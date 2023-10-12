"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

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
from django.db.models import Q, Sum, QuerySet, F
from django.db.models.functions import Coalesce
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import (ASSET_CA_CASH, GROUP_CFS_FIN_DIVIDENDS, GROUP_CFS_FIN_ISSUING_EQUITY,
                                    GROUP_CFS_FIN_LT_DEBT_PAYMENTS, GROUP_CFS_FIN_ST_DEBT_PAYMENTS,
                                    GROUP_CFS_INVESTING_AND_FINANCING, GROUP_CFS_INVESTING_PPE,
                                    GROUP_CFS_INVESTING_SECURITIES, validate_roles)
from django_ledger.models.accounts import CREDIT, DEBIT
from django_ledger.models.entity import EntityStateModel, EntityModel
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.transactions import TransactionModelQuerySet, TransactionModel
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import (DJANGO_LEDGER_JE_NUMBER_PREFIX, DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
                                    DJANGO_LEDGER_JE_NUMBER_NO_UNIT_PREFIX)


class JournalEntryValidationError(ValidationError):
    pass


class JournalEntryModelQuerySet(QuerySet):
    """
    Custom defined JournalEntryQuerySet.
    """

    def create(self, verify_on_save: bool = False, force_create: bool = False, **kwargs):
        """
        Overrides the standard Django QuerySet create() method to avoid the creation of POSTED Journal Entries without
        proper business logic validation. New JEs using the create() method don't have any transactions to validate.
        therefore, it is not necessary to query DB to balance TXS

        Parameters
        ----------

        verify_on_save: bool
            Executes a Journal Entry verification hook before saving. Avoids additional queries to
            validate the Journal Entry

        force_create: bool
            If True, will create return a new JournalEntryModel even if Posted at time of creation.
            Use only if you know what you are doing.

        Returns
        -------
        JournalEntryModel
            The newly created Journal Entry Model.
        """
        is_posted = kwargs.get('posted')

        if is_posted and not force_create:
            raise FieldError('Cannot create Journal Entries as posted')

        obj = self.model(**kwargs)
        self._for_write = True

        # verify_on_save option avoids additional queries to validate the journal entry.
        # New JEs using the create() method don't have any transactions to validate.
        # therefore, it is not necessary to query DB to balance TXS.
        obj.save(force_insert=True, using=self.db, verify=verify_on_save)
        return obj

    def posted(self):
        """
        Filters the QuerySet to only posted Journal Entries.

        Returns
        -------
        JournalEntryModelQuerySet
            A QuerySet with applied filters.
        """
        return self.filter(posted=True)

    def unposted(self):
        return self.filter(posted=False)

    def locked(self):
        """
        Filters the QuerySet to only locked Journal Entries.

        Returns
        -------
        JournalEntryModelQuerySet
            A QuerySet with applied filters.
        """

        return self.filter(locked=True)

    def unlocked(self):
        return self.filter(locked=False)


class JournalEntryModelManager(models.Manager):
    """
    A custom defined Journal Entry Model Manager that supports additional complex initial Queries based on the
    EntityModel and authenticated UserModel.
    """

    def for_entity(self, entity_slug, user_model):
        """
        Fetches a QuerySet of JournalEntryModels associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        __________
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model
            Logged in and authenticated django UserModel instance.

        Examples
        ________
            >>> request_user = request.user
            >>> slug = kwargs['entity_slug'] # may come from request kwargs
            >>> journal_entry_qs = JournalEntryModel.objects.for_entity(user_model=request_user, entity_slug=slug)

        Returns
        _______
        JournalEntryModelQuerySet
            Returns a JournalEntryModelQuerySet with applied filters.
        """
        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return self.get_queryset().filter(
                Q(ledger__entity=entity_slug) &
                (
                        Q(ledger__entity__admin=user_model) |
                        Q(ledger__entity__managers__in=[user_model])
                )

            )
        return self.get_queryset().filter(
            Q(ledger__entity__slug__iexact=entity_slug) &
            (
                    Q(ledger__entity__admin=user_model) |
                    Q(ledger__entity__managers__in=[user_model])
            )

        )

    def for_ledger(self, ledger_pk: Union[str, UUID], entity_slug, user_model):
        """
        Fetches a QuerySet of JournalEntryModels associated with a specific EntityModel & UserModel & LedgerModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        __________
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model
            Logged in and authenticated django UserModel instance.
        ledger_pk: str or UUID
            The LedgerModel uuid as a string or UUID.

        Examples
        ________
            >>> request_user = request.user
            >>> slug = kwargs['entity_slug'] # may come from request kwargs
            >>> ledger_pk = kwargs['ledger_pk'] # may come from request kwargs
            >>> journal_entry_qs = JournalEntryModel.objects.for_ledger(ledger_pk=ledger_pk, user_model=request_user, entity_slug=slug)

        Returns
        _______
        JournalEntryModelQuerySet
            Returns a JournalEntryModelQuerySet with applied filters.
        """
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(ledger__uuid__exact=ledger_pk)


class ActivityEnum(Enum):
    """
    The database string representation of each accounting activity prefix in the database.

    Attributes
    __________

    OPERATING: str
        The database representation prefix of a Journal Entry that is an Operating Activity.

    INVESTING: str
        The database representation prefix of a Journal Entry that is an Investing Activity.

    FINANCING: str
        The database representation prefix of a Journal Entry that is an Financing Activity.
    """
    OPERATING = 'op'
    INVESTING = 'inv'
    FINANCING = 'fin'


class JournalEntryModelAbstract(CreateUpdateMixIn):
    """
    The base implementation of the JournalEntryModel.

    Attributes
    ----------
    uuid: UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().
    je_number: str
        A unique, sequential, human-readable alphanumeric Journal Entry Number (a.k.a Voucher or Document Number in
        other commercial bookkeeping software). Contains the fiscal year under which the JE takes place within the
        EntityModel as a prefix.
    timestamp: datetime
        The date of the JournalEntryModel. This date is applied to all TransactionModels contained within the JE, and
        drives the financial statements of the EntityModel.
    description: str
        A user defined description for the JournalEntryModel.
    entity_unit: EntityUnitModel
        A logical, self-contained, user defined class or structure defined withing the EntityModel.
        See EntityUnitModel documentation for more details.
    activity: str
        Programmatically determined based on the JE transactions and must be a value from ACTIVITIES. Gives
        additional insight of the nature of the JournalEntryModel in order to produce the Statement of Cash Flows for the
        EntityModel.
    origin: str
        A string giving additional information behind the origin or trigger of the JournalEntryModel.
        For example: reconciliations, migrations, auto-generated, etc. Any string value is valid. Max 30 characters.
    posted: bool
        Determines if the JournalLedgerModel is posted, which means is affecting the books. Defaults to False.
    locked: bool
        Determines  if the JournalEntryModel is locked, which the creation or updates of new transactions are not
        allowed.
    ledger: LedgerModel
        The LedgerModel associated with this JournalEntryModel. Cannot be null.
    """
    OPERATING_ACTIVITY = ActivityEnum.OPERATING.value
    FINANCING_OTHER = ActivityEnum.FINANCING.value
    INVESTING_OTHER = ActivityEnum.INVESTING.value

    INVESTING_SECURITIES = f'{ActivityEnum.INVESTING.value}_securities'
    INVESTING_PPE = f'{ActivityEnum.INVESTING.value}_ppe'

    FINANCING_STD = f'{ActivityEnum.FINANCING.value}_std'
    FINANCING_LTD = f'{ActivityEnum.FINANCING.value}_ltd'
    FINANCING_EQUITY = f'{ActivityEnum.FINANCING.value}_equity'
    FINANCING_DIVIDENDS = f'{ActivityEnum.FINANCING.value}_dividends'

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

    VALID_ACTIVITIES = list(chain.from_iterable([[a[0] for a in cat[1]] for cat in ACTIVITIES]))
    MAP_ACTIVITIES = dict(chain.from_iterable([[(a[0], cat[0]) for a in cat[1]] for cat in ACTIVITIES]))
    NON_OPERATIONAL_ACTIVITIES = [a for a in VALID_ACTIVITIES if ActivityEnum.OPERATING.value not in a]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    je_number = models.SlugField(max_length=25, editable=False, verbose_name=_('Journal Entry Number'))
    timestamp = models.DateTimeField(verbose_name=_('Timestamp'), default=localtime)
    description = models.CharField(max_length=70, blank=True, null=True, verbose_name=_('Description'))
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel',
                                    on_delete=models.RESTRICT,
                                    blank=True,
                                    null=True,
                                    verbose_name=_('Associated Entity Unit'))
    activity = models.CharField(choices=ACTIVITIES,
                                max_length=20,
                                null=True,
                                blank=True,
                                editable=False,
                                verbose_name=_('Activity'))
    origin = models.CharField(max_length=30, blank=True, null=True, verbose_name=_('Origin'))
    posted = models.BooleanField(default=False, verbose_name=_('Posted'))
    locked = models.BooleanField(default=False, verbose_name=_('Locked'))
    is_closing_entry = models.BooleanField(default=False)

    # todo: rename to ledger_model?
    ledger = models.ForeignKey('django_ledger.LedgerModel',
                               verbose_name=_('Ledger'),
                               related_name='journal_entries',
                               on_delete=models.CASCADE)

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

    def __str__(self):
        if self.je_number:
            return 'JE: {x1} - Desc: {x2}'.format(x1=self.je_number, x2=self.description)
        return 'JE ID: {x1} - Desc: {x2}'.format(x1=self.pk, x2=self.description)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._verified = False
        self._last_closing_date: Optional[date] = None

    def can_post(self, ignore_verify: bool = True) -> bool:
        """
        Determines if a JournalEntryModel can be posted.

        Parameters
        ----------
        ignore_verify: bool
            Skips JournalEntryModel verification if True. Defaults to False.

        Returns
        -------
        bool
            True if JournalEntryModel can be posted, otherwise False.
        """

        return all([
            self.is_locked(),
            not self.is_posted(),
            self.is_verified() if not ignore_verify else True,
            not self.ledger.is_locked(),
            not self.is_in_locked_period()
        ])

    def can_unpost(self) -> bool:
        """
        Determines if a JournalEntryModel can be un-posted.

        Returns
        -------
        bool
            True if JournalEntryModel can be un-posted, otherwise False.
        """
        return all([
            self.is_posted(),
            not self.ledger.is_locked(),
            not self.is_in_locked_period()
        ])

    def can_lock(self) -> bool:
        """
        Determines if a JournalEntryModel can be locked.
        Locked JournalEntryModels cannot be modified.

        Returns
        -------
        bool
            True if JournalEntryModel can be locked, otherwise False.
        """
        return all([
            not self.is_locked(),
            not self.ledger.is_locked()
        ])

    def can_unlock(self) -> bool:
        """
        Determines if a JournalEntryModel can be un-locked.
        Locked transactions cannot be modified.

        Returns
        -------
        bool
            True if JournalEntryModel can be un-locked, otherwise False.
        """
        return all([
            self.is_locked(),
            not self.is_posted(),
            not self.is_in_locked_period(),
            not self.ledger.is_locked()
        ])

    def can_delete(self) -> bool:
        return all([
            not self.is_locked(),
            not self.is_posted(),
        ])

    def can_edit_timestamp(self) -> bool:
        return not self.is_locked()

    def is_posted(self):
        return self.posted is True

    def is_in_locked_period(self, new_timestamp: Optional[Union[date, datetime]] = None) -> bool:
        last_closing_date = self.get_entity_last_closing_date()
        if last_closing_date is not None:
            if not new_timestamp:
                return last_closing_date >= self.timestamp.date()
            elif isinstance(new_timestamp, datetime):
                return last_closing_date >= new_timestamp.date()
            else:
                return last_closing_date >= new_timestamp
        return False

    def is_locked(self):
        if self.is_posted():
            return True
        return any([
            self.locked is True,
            any([
                self.is_in_locked_period(),
                self.ledger.is_locked()
            ])
        ])

    def is_verified(self) -> bool:
        """
        Determines if the JournalEntryModel is verified.

        Returns
        -------
        bool
            True if is verified, otherwise False.
        """
        return self._verified

    def is_balance_valid(self, txs_qs: Optional[TransactionModelQuerySet] = None) -> bool:
        """
        Checks if CREDITs and DEBITs are equal.

        Parameters
        ----------
        txs_qs: TransactionModelQuerySet
            Optional pre-fetched JE instance TransactionModelQuerySet. Will be validated if provided.

        Returns
        -------
        bool
            True if JE balances are valid (i.e. are equal).
        """
        if len(txs_qs) > 0:
            balances = self.get_txs_balances(txs_qs=txs_qs, as_dict=True)
            return balances[CREDIT] == balances[DEBIT]
        return True

    def is_cash_involved(self, txs_qs=None):
        return ASSET_CA_CASH in self.get_txs_roles(txs_qs=None)

    def is_operating(self):
        return self.activity in [
            self.OPERATING_ACTIVITY
        ]

    def is_financing(self):
        return self.activity in [
            self.FINANCING_EQUITY,
            self.FINANCING_LTD,
            self.FINANCING_DIVIDENDS,
            self.FINANCING_STD,
            self.FINANCING_OTHER
        ]

    def is_investing(self):
        return self.activity in [
            self.INVESTING_SECURITIES,
            self.INVESTING_PPE,
            self.INVESTING_OTHER
        ]

    def is_txs_qs_valid(self, txs_qs: TransactionModelQuerySet, raise_exception: bool = True) -> bool:
        """
        Validates a given TransactionModelQuerySet against the JournalEntryModel instance.

        Parameters
        ----------
        txs_qs: TransactionModelQuerySet
            The queryset to validate.

        raise_exception: bool
            Raises JournalEntryValidationError if TransactionModelQuerySet is not valid.

        Raises
        ------
        JournalEntryValidationError if JE model is invalid and raise_exception is True.

        Returns
        -------
        bool
            True if valid, otherwise False.
        """
        if not isinstance(txs_qs, TransactionModelQuerySet):
            raise JournalEntryValidationError('Must pass an instance of TransactionModelQuerySet')

        is_valid = all(tx.journal_entry_id == self.uuid for tx in txs_qs)
        if not is_valid and raise_exception:
            raise JournalEntryValidationError('Invalid TransactionModelQuerySet provided. All Transactions must be ',
                                              f'associated with LedgerModel {self.uuid}')
        return is_valid

    def get_absolute_url(self) -> str:

        return reverse('django_ledger:je-detail',
                       kwargs={
                           'je_pk': self.id,
                           'ledger_pk': self.ledger_id,
                           # pylint: disable=no-member
                           'entity_slug': self.ledger.entity.slug
                       })

    def get_entity_unit_name(self, no_unit_name: str = ''):
        if self.entity_unit_id:
            return self.entity_unit.name
        return no_unit_name

    def get_entity_last_closing_date(self) -> Optional[date]:
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
                raise JournalEntryValidationError(
                    message=_('Cannot post an empty Journal Entry.')
                )

        if force_lock and not self.is_locked():
            self.mark_as_locked(commit=False, raise_exception=True)

        if not self.can_post(ignore_verify=False):
            if raise_exception:
                raise JournalEntryValidationError(f'Journal Entry {self.uuid} cannot post.'
                                                  f' Is verified: {self.is_verified()}')
        else:
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
        else:
            if self.is_posted():
                self.posted = False
                self.activity = None
                if not self.is_posted():
                    if commit:
                        self.save(verify=False,
                                  update_fields=[
                                      'posted',
                                      'activity',
                                      'updated'
                                  ])

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
                raise JournalEntryValidationError(f'Journal Entry {self.uuid} is already locked.')
        else:
            if not self.is_locked():
                self.generate_activity(force_update=True)
                self.locked = True
                if self.is_locked():
                    if commit:
                        self.save(verify=False)

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
        else:
            if self.is_locked():
                self.locked = False
                if not self.is_locked():
                    if commit:
                        self.save(verify=False)

    def get_transaction_queryset(self, select_accounts: bool = True) -> TransactionModelQuerySet:
        """
        Fetches the TransactionModelQuerySet associated with the JournalEntryModel instance.

        Parameters
        ----------
        select_accounts: bool
            Fetches the associated AccountModel of each transaction. Defaults to True.

        Returns
        -------
        TransactionModelQuerySet
            The TransactionModelQuerySet associated with the current JournalEntryModel instance.
        """
        if select_accounts:
            return self.transactionmodel_set.all().select_related('account')
        return self.transactionmodel_set.all()

    def get_txs_balances(self,
                         txs_qs: Optional[TransactionModelQuerySet] = None,
                         as_dict: bool = False) -> Union[TransactionModelQuerySet, Dict]:
        """
        Fetches the sum total of CREDITs and DEBITs associated with the JournalEntryModel instance. This method
        performs a reduction/aggregation at the database level and fetches exactly two records. Optionally,
        may pass an  existing TransactionModelQuerySet if previously fetched. Additional validation occurs to ensure
        that all TransactionModels in QuerySet are of the JE instance. Due to JournalEntryModel pre-save validation
        and basic rules of accounting, CREDITs and DEBITS will always match.

        Parameters
        ----------
        txs_qs: TransactionModelQuerySet
            The JE TransactionModelQuerySet to use if previously fetched. Will be validated to make sure all
            TransactionModel in QuerySet belong to the JournalEntryModel instance.

        as_dict: bool
            If True, returns the result as a dictionary, with exactly two keys: 'credit' and 'debit'.
            The values will be the total CREDIT or DEBIT amount as Decimal.

        Examples
        --------
        >>> je_model: JournalEntryModel = je_qs.first() # any existing JournalEntryModel QuerySet...
        >>> balances = je_model.get_txs_balances()
        >>> balances
        Returns exactly two records:
        <TransactionModelQuerySet [{'tx_type': 'credit', 'amount__sum': Decimal('2301.5')},
        {'tx_type': 'debit', 'amount__sum': Decimal('2301.5')}]>

        Examples
        --------
        >>> balances = je_model.get_txs_balances(as_dict=True)
        >>> balances
        Returns a dictionary:
        {'credit': Decimal('2301.5'), 'debit': Decimal('2301.5')}

        Raises
        ------
        JournalEntryValidationError
            If JE is not valid or TransactionModelQuerySet provided does not belong to JE instance.

        Returns
        -------
        TransactionModelQuerySet or dict
            An aggregated queryset containing exactly two records. The total CREDIT or DEBIT amount as Decimal.
        """
        if not txs_qs:
            txs_qs = self.get_transaction_queryset(select_accounts=False)
        else:
            if not isinstance(txs_qs, TransactionModelQuerySet):
                raise JournalEntryValidationError(
                    message=f'Must pass a TransactionModelQuerySet. Got {txs_qs.__class__.__name__}'
                )

            # todo: add maximum transactions per JE model as a setting...
            is_valid = self.is_txs_qs_valid(txs_qs)
            if not is_valid:
                raise JournalEntryValidationError(
                    message='Invalid Transaction QuerySet used. Must be from same Journal Entry'
                )

        balances = txs_qs.values('tx_type').annotate(
            amount__sum=Coalesce(Sum('amount'),
                                 Decimal('0.00'),
                                 output_field=models.DecimalField()))

        if as_dict:
            return {
                tx['tx_type']: tx['amount__sum'] for tx in balances
            }
        return balances

    def get_txs_roles(self,
                      txs_qs: Optional[TransactionModelQuerySet] = None,
                      exclude_cash_role: bool = False) -> Set[str]:
        """
        Determines the list of account roles involved in the JournalEntryModel instance.
        It reaches into the AccountModel associated with each TransactionModel of the JE to determine a Set of
        all roles involved in transactions. This method is important in determining the nature of the

        Parameters
        ----------
        txs_qs: TransactionModelQuerySet
            Prefetched TransactionModelQuerySet. Will be validated if provided.
            Avoids additional DB query if provided.

        exclude_cash_role: bool
            Removes CASH role from the Set if present.
            Useful in some cases where cash role must be excluded for additional validation.

        Returns
        -------
        set
            The set of account roles as strings associated with the JournalEntryModel instance.
        """
        if not txs_qs:
            txs_qs = self.get_transaction_queryset(select_accounts=True)
        else:
            self.is_txs_qs_valid(txs_qs)

        # todo: implement distinct for non SQLite Backends...
        if exclude_cash_role:
            return set([i.account.role for i in txs_qs if i.account.role != ASSET_CA_CASH])
        return set([i.account.role for i in txs_qs])

    def has_activity(self) -> bool:
        return self.activity is not None

    def get_activity_name(self) -> Optional[str]:
        """
        Returns a human-readable, GAAP string representing the JournalEntryModel activity.

        Returns
        -------
        str or None
            Representing the JournalEntryModel activity in the statement of cash flows.
        """
        if self.activity:
            if self.is_operating():
                return ActivityEnum.OPERATING.value
            elif self.is_investing():
                return ActivityEnum.INVESTING.value
            elif self.is_financing():
                return ActivityEnum.FINANCING.value

    @classmethod
    def get_activity_from_roles(cls,
                                role_set: Union[List[str], Set[str]],
                                validate: bool = False,
                                raise_exception: bool = True) -> Optional[str]:

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
                    self.activity = self.get_activity_from_roles(role_set=role_list)
        return self.activity

    # todo: add entity_model as parameter on all functions...
    # todo: outsource this function to EntityStateModel...?...
    def _get_next_state_model(self, raise_exception: bool = True) -> EntityStateModel:

        entity_model = EntityModel.objects.get(uuid__exact=self.ledger.entity_id)
        fy_key = entity_model.get_fy_for_date(dt=self.timestamp)

        try:
            LOOKUP = {
                'entity_model_id__exact': self.ledger.entity_id,
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
        Checks if the JournalEntryModel instance can generate its own JE number.
        Conditions are:
        * The JournalEntryModel must have a LedgerModel instance assigned.
        * The JournalEntryModel instance must not have a pre-existing JE number.

        Returns
        -------
        bool
            True if JournalEntryModel needs a JE number, otherwise False.
        """
        return all([
            self.ledger_id,
            not self.je_number
        ])

    def generate_je_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next Journal Entry document number available. The operation
        will result in two additional queries if the Journal Entry LedgerModel & EntityUnitModel are not cached in
        QuerySet via select_related('ledger', 'entity_unit').

        Parameters
        ----------
        commit: bool
            Commits transaction into JournalEntryModel when function is called.

        Returns
        -------
        str
            A String, representing the new or current JournalEntryModel instance Document Number.
        """
        if self.can_generate_je_number():

            with transaction.atomic(durable=True):

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
        Verifies the JournalEntryModel. The JE Model is verified when:
            * All TransactionModels associated with the JE instance are in balance (i.e. the sum of CREDITs and DEBITs are equal).
            * If the JournalEntryModel is using cash, a cash flow activity is assigned.

        Parameters
        ----------
        txs_qs: TransactionModelQuerySet
            Prefetched TransactionModelQuerySet. If provided avoids additional DB query. Will be verified against
            JournalEntryModel instance.
        force_verify: bool
            If True, forces new verification of JournalEntryModel if previously verified. Defaults to False.
        raise_exception: bool
            If True, will raise JournalEntryValidationError if verification fails.
        kwargs: dict
            Additional function key-word args.

        Raises
        ------
        JournalEntryValidationError if JE instance could not be verified.

        Returns
        -------
        tuple: TransactionModelQuerySet, bool
            The TransactionModelQuerySet of the JournalEntryModel instance, verification result as True/False.
        """

        if not self.is_verified() or force_verify:
            self._verified = False

            # fetches JEModel TXS QuerySet if not provided....
            if not txs_qs:
                txs_qs = self.get_transaction_queryset()
                is_txs_qs_valid = True
            else:
                try:
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

            # if not len(txs_qs):
            #     if raise_exception:
            #         raise JournalEntryValidationError('Journal entry has no transactions.')

            # if len(txs_qs) < 2:
            #     if raise_exception:
            #         raise JournalEntryValidationError('At least two transactions required.')

            if all([is_balance_valid, is_txs_qs_valid]):
                # activity flag...
                self.generate_activity(txs_qs=txs_qs, raise_exception=raise_exception)
                self._verified = True
                return txs_qs, self.is_verified()
        return TransactionModel.objects.none(), self.is_verified()

    def clean(self,
              verify: bool = False,
              raise_exception: bool = True,
              txs_qs: Optional[TransactionModelQuerySet] = None) -> Tuple[TransactionModelQuerySet, bool]:
        """
        Customized JournalEntryModel clean method. Generates a JE number if needed. Optional verification hook on clean.

        Parameters
        ----------
        raise_exception: bool
            Raises exception if JE could not be verified. Defaults to True.
        verify: bool
            Attempts to verify the JournalEntryModel during cleaning.
        txs_qs: TransactionModelQuerySet
            Prefetched TransactionModelQuerySet. If provided avoids additional DB query. Will be verified against
            JournalEntryModel instance.

        Returns
        -------
        tuple: TransactionModelQuerySet, bool
            The TransactionModelQuerySet of the JournalEntryModel instance, verification result as True/False.
        """

        if txs_qs:
            self.is_txs_qs_valid(txs_qs=txs_qs)

        if not self.timestamp:
            self.timestamp = localtime()
        elif self.timestamp and self.timestamp > localtime():
            raise JournalEntryValidationError(message='Cannot create JE Models with timestamp in the future.')

        self.generate_je_number(commit=True)
        if verify:
            txs_qs, verified = self.verify()
            return txs_qs, self.is_verified()
        return TransactionModel.objects.none(), self.is_verified()

    def get_delete_message(self) -> str:
        return _(f'Are you sure you want to delete JournalEntry Model {self.description} on Ledger {self.ledger.name}?')

    def delete(self, **kwargs):
        if not self.can_delete():
            raise JournalEntryValidationError(
                message=_(f'JournalEntryModel {self.uuid} cannot be deleted...')
            )
        return super().delete(**kwargs)

    def save(self,
             verify: bool = True,
             post_on_verify: bool = False,
             *args, **kwargs):
        # todo this does not show up on docs...
        """
        Custom JournalEntryModel instance save method. Additional options are added to attempt to verify JournalEntryModel
        before saving into database.

        Parameters
        ----------
        verify: bool
            If True, verifies JournalEntryModel transactions before saving. Defaults to True.
        post_on_verify: bool
            Posts JournalEntryModel if verification is successful and can_post() is True.

        Returns
        -------
        JournalEntryModel
            The saved instance.
        """
        try:
            self.generate_je_number(commit=False)
            if verify:
                txs_qs, is_verified = self.clean(verify=True)
                if self.is_verified() and post_on_verify:
                    # commit is False since the super call takes place at the end of save()
                    # self.mark_as_locked(commit=False, raise_exception=True)
                    self.mark_as_posted(commit=False, verify=False, force_lock=True, raise_exception=True)
        except ValidationError as e:
            if self.can_unpost():
                self.mark_as_unposted(raise_exception=True)
            raise JournalEntryValidationError(
                f'Something went wrong validating journal entry ID: {self.uuid}: {e.message}')
        except Exception as e:
            # safety net, for any unexpected error...
            # no JE can be posted if not fully validated...
            self.posted = False
            self._verified = False
            self.save(update_fields=['posted', 'updated'], verify=False)
            raise JournalEntryValidationError(e)

        if not self.is_verified() and verify:
            raise JournalEntryValidationError(message='Cannot save an unverified Journal Entry.')

        return super(JournalEntryModelAbstract, self).save(*args, **kwargs)


class JournalEntryModel(JournalEntryModelAbstract):
    """
    Journal Entry Model Base Class From Abstract
    """


def journalentrymodel_presave(instance: JournalEntryModel, **kwargs):
    if instance._state.adding and not instance.ledger.can_edit_journal_entries():
        raise JournalEntryValidationError(
            message=_(f'Cannot add Journal Entries to locked LedgerModel {instance.ledger_id}')
        )


pre_save.connect(journalentrymodel_presave, sender=JournalEntryModel)
