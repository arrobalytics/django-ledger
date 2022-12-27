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
from decimal import Decimal
from enum import Enum
from itertools import chain
from typing import Set, Union
from uuid import uuid4, UUID

from django.core.exceptions import FieldError, ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Sum, QuerySet, F
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.exceptions import JournalEntryValidationError
from django_ledger.io.roles import (ASSET_CA_CASH, GROUP_CFS_FIN_DIVIDENDS, GROUP_CFS_FIN_ISSUING_EQUITY,
                                    GROUP_CFS_FIN_LT_DEBT_PAYMENTS, GROUP_CFS_FIN_ST_DEBT_PAYMENTS,
                                    GROUP_CFS_INVESTING_AND_FINANCING, GROUP_CFS_INV_PURCHASE_OR_SALE_OF_PPE,
                                    GROUP_CFS_INV_LTD_OF_PPE, GROUP_CFS_INV_PURCHASE_OF_SECURITIES,
                                    GROUP_CFS_INV_LTD_OF_SECURITIES, GROUP_CFS_INVESTING_PPE,
                                    GROUP_CFS_INVESTING_SECURITIES)
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import (DJANGO_LEDGER_JE_NUMBER_PREFIX, DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
                                    DJANGO_LEDGER_JE_NUMBER_NO_UNIT_PREFIX)


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

    def locked(self):
        """
        Filters the QuerySet to only locked Journal Entries.

        Returns
        -------
        JournalEntryModelQuerySet
            A QuerySet with applied filters.
        """

        return self.filter(locked=True)


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
    __________
    uuid : UUID
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
    NON_OPERATIONAL_ACTIVITIES = [a for a in VALID_ACTIVITIES if ActivityEnum.OPERATING.value not in a]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    je_number = models.SlugField(max_length=20, editable=False, verbose_name=_('Journal Entry Number'))
    timestamp = models.DateTimeField(verbose_name=_('Date'))
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

    # todo: rename to ledger_model?
    ledger = models.ForeignKey('django_ledger.LedgerModel',
                               verbose_name=_('Ledger'),
                               related_name='journal_entries',
                               on_delete=models.CASCADE)

    on_coa = JournalEntryModelManager.from_queryset(queryset_class=JournalEntryModelQuerySet)()
    objects = JournalEntryModelManager.from_queryset(queryset_class=JournalEntryModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Journal Entry')
        verbose_name_plural = _('Journal Entries')
        indexes = [
            # models.Index(fields=['parent']),
            models.Index(fields=['ledger']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['activity']),
            models.Index(fields=['entity_unit']),
            models.Index(fields=['locked']),
            models.Index(fields=['posted']),
            models.Index(fields=['je_number'])
        ]

    def __str__(self):
        if self.je_number:
            return 'JE: {x1} - Desc: {x2}'.format(x1=self.je_number, x2=self.description)
        return 'JE ID: {x1} - Desc: {x2}'.format(x1=self.pk, x2=self.description)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._verified = False

    def is_verified(self) -> bool:
        return self._verified

    def get_absolute_url(self):
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

    def can_post(self, ignore_verify: bool = True) -> bool:
        return all([
            not self.locked,
            not self.posted,
            self.is_verified() if not ignore_verify else True
        ])

    def can_unpost(self):
        return all([
            not self.locked,
            self.posted
        ])

    def can_lock(self):
        return all([
            not self.locked
        ])

    def can_unlock(self):
        return all([
            self.locked
        ])

    def mark_as_posted(self,
                       commit: bool = False,
                       verify: bool = False,
                       raise_exception: bool = False,
                       **kwargs):
        if verify:
            txs_qs = self.verify()

        if not self.can_post(ignore_verify=False):
            if raise_exception:
                raise JournalEntryValidationError(f'Journal Entry {self.uuid} cannot be posted.'
                                                  f' Is verified: {self.is_verified()}')
        else:
            self.posted = True
            if commit:
                self.save(verify=False,
                          update_fields=[
                              'posted',
                              'activity',
                              'updated'
                          ])

    def mark_as_unposted(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        if not self.can_unpost():
            if raise_exception:
                raise JournalEntryValidationError(f'Journal Entry {self.uuid} is unposted.')
        else:
            self.posted = False
            if commit:
                self.save(verify=False,
                          update_fields=[
                              'posted',
                              'updated'
                          ])

    def mark_as_locked(self, commit: bool = False, raise_exception: bool = False, **kwargs):

        if not self.can_lock():
            if raise_exception:
                raise ValidationError(f'Journal Entry {self.uuid} is already locked.')
        else:
            self.locked = True
            if commit:
                self.save(verify=False,
                          update_fields=[
                              'locked',
                              'updated'
                          ])

    def mark_as_unlocked(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        if not self.can_unlock():
            if raise_exception:
                raise ValidationError(f'Journal Entry {self.uuid} is already unlocked.')
        else:
            self.locked = False
            if commit:
                self.save(verify=False,
                          update_fields=[
                              'locked',
                              'updated'
                          ])

    def get_txs_qs(self, select_accounts: bool = True):
        if not select_accounts:
            return self.transactionmodel_set.all()
        return self.transactionmodel_set.all().select_related('account')

    def get_txs_balances(self, txs_qs=None):
        if not txs_qs:
            txs_qs = self.get_txs_qs()
        balances = txs_qs.values('tx_type').annotate(
            amount__sum=Coalesce(Sum('amount'),
                                 Decimal('0.00'),
                                 output_field=models.DecimalField()))
        return balances

    def get_txs_roles(self, txs_qs=None, exclude_cash_role: bool = False) -> Set:
        if not txs_qs:
            txs_qs = self.get_txs_qs()

        # todo: implement distinct for non SQLite Backends...
        if exclude_cash_role:
            roles_involved = [i.account.role for i in txs_qs if i.account.role != ASSET_CA_CASH]
        else:
            roles_involved = [i.account.role for i in txs_qs]
        return set(roles_involved)

    def is_balance_valid(self, txs_qs=None):
        if len(txs_qs) > 0:
            balances = self.get_txs_balances(txs_qs=txs_qs)
            bal_idx = {i['tx_type']: i['amount__sum'] for i in balances}
            return bal_idx['credit'] == bal_idx['debit']
        return True

    def is_cash_involved(self, txs_qs=None):
        return ASSET_CA_CASH in self.get_txs_roles(txs_qs=None)

    def verify(self,
               txs_qs=None,
               force_verify: bool = False,
               raise_exception: bool = True,
               **kwargs):
        if not self.is_verified() or force_verify:
            txs_qs = self.get_txs_qs()

            # if not len(txs_qs):
            #     if raise_exception:
            #         raise JournalEntryValidationError('Journal entry has no transactions.')

            # if len(txs_qs) < 2:
            #     if raise_exception:
            #         raise JournalEntryValidationError('At least two transactions required.')

            # CREDIT/DEBIT Balance validation...
            balance_is_valid = self.is_balance_valid(txs_qs)
            if not balance_is_valid:
                if raise_exception:
                    raise JournalEntryValidationError('Debits and credits do not match.')

            # activity flag...
            cash_is_involved = self.is_cash_involved(txs_qs)
            if not cash_is_involved:
                self.activity = None
            else:
                roles_involved = self.get_txs_roles(txs_qs, exclude_cash_role=True)

                # determining if investing....
                is_investing_for_ppe = all([
                    all([r in GROUP_CFS_INVESTING_PPE for r in roles_involved]),  # all roles must be in group
                    sum([r in GROUP_CFS_INV_PURCHASE_OR_SALE_OF_PPE for r in roles_involved]) > 0,  # at least one role
                    sum([r in GROUP_CFS_INV_LTD_OF_PPE for r in roles_involved]) > 0,  # at least one role
                ])
                is_investing_for_securities = all([
                    all([r in GROUP_CFS_INVESTING_SECURITIES for r in roles_involved]),  # all roles must be in group
                    sum([r in GROUP_CFS_INV_PURCHASE_OF_SECURITIES for r in roles_involved]) > 0,  # at least one role
                    sum([r in GROUP_CFS_INV_LTD_OF_SECURITIES for r in roles_involved]) > 0,  # at least one role
                ])

                # determining if financing...
                is_financing_dividends = all([r in GROUP_CFS_FIN_DIVIDENDS for r in roles_involved])
                is_financing_issuing_equity = all([r in GROUP_CFS_FIN_ISSUING_EQUITY for r in roles_involved])
                is_financing_st_debt = all([r in GROUP_CFS_FIN_ST_DEBT_PAYMENTS for r in roles_involved])
                is_financing_lt_debt = all([r in GROUP_CFS_FIN_LT_DEBT_PAYMENTS for r in roles_involved])

                is_operating = all([r not in GROUP_CFS_INVESTING_AND_FINANCING for r in roles_involved])

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
                        raise JournalEntryValidationError(f'Multiple activities detected in roles JE {roles_involved}.')
                else:
                    if is_investing_for_ppe:
                        self.activity = self.INVESTING_PPE
                    elif is_investing_for_securities:
                        self.activity = self.INVESTING_SECURITIES

                    elif is_financing_st_debt:
                        self.activity = self.FINANCING_STD
                    elif is_financing_lt_debt:
                        self.activity = self.FINANCING_LTD
                    elif is_financing_issuing_equity:
                        self.activity = self.FINANCING_EQUITY
                    elif is_financing_dividends:
                        self.activity = self.FINANCING_DIVIDENDS
                    elif is_operating:
                        self.activity = self.OPERATING_ACTIVITY
                    else:
                        if raise_exception:
                            raise JournalEntryValidationError(f'No activity match for roles {roles_involved}.'
                                                              'Split into multiple Journal Entries or check'
                                                              ' your account selection.')
            self._verified = True
            return txs_qs
        self._verified = False

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

    def get_activity(self):
        if self.activity:
            if self.is_operating():
                return ActivityEnum.OPERATING.value
            elif self.is_investing():
                return ActivityEnum.INVESTING.value
            elif self.is_financing():
                return ActivityEnum.FINANCING.value

    def _get_next_state_model(self, raise_exception: bool = True):

        EntityStateModel = lazy_loader.get_entity_state_model()
        EntityModel = lazy_loader.get_entity_model()
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
        return all([
            self.ledger_id,
            not self.je_number
        ])

    def generate_je_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next Journal Entry document number available. The operation
        will result in two additional queries if the Journal Entry LedgerModel & EntityUnitModel are not cached in
        QuerySet via select_related('ledger', 'entity_unit').
        @param commit: Commit transaction into Journal Entry.
        @return: A String, representing the current JournalEntryModel instance Document Number.
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

    def clean(self, verify: bool = False):
        self.generate_je_number(commit=True)
        if verify:
            txs_qs = self.verify()
            return txs_qs

    def save(self, verify: bool = False, post_on_verify: bool = False, *args, **kwargs):
        try:
            self.generate_je_number(commit=False)
            if verify:
                self.clean(verify=verify)
                if self.is_verified() and post_on_verify:
                    # commit is False since the super call takes place at the end of save()
                    self.mark_as_posted(commit=False, raise_exception=True)
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

        super(JournalEntryModelAbstract, self).save(*args, **kwargs)


class JournalEntryModel(JournalEntryModelAbstract):
    """
    Journal Entry Model Base Class From Abstract
    """
