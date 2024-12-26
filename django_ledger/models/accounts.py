"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

AccountModel
------------
The AccountModel is a fundamental component of the Django Ledger system, responsible for categorizing and organizing
financial transactions related to an entity's assets, liabilities, and equity.

Account Types
-------------

In accordance with accounting principles, each AccountModel must be classified as either:

1. **DEBIT-type balance account**
2. **CREDIT-type balance account**

The account type determines how transactions affect the account's balance.

Double Entry Accounting
-----------------------

The AccountModel is crucial in implementing double entry accounting systems:

* For DEBIT-type accounts:
  - A DEBIT increases the balance
  - A CREDIT decreases the balance

* For CREDIT-type accounts:
  - A CREDIT increases the balance
  - A DEBIT decreases the balance

Chart of Accounts
-----------------

Users have the flexibility to adopt a chart of accounts that best suits their EntityModel. Django Ledger provides a
default Chart of Accounts when creating a new EntityModel, which can be customized as needed.

Account Roles
-------------

All AccountModels must be assigned a role from the `ACCOUNT_ROLES` function in `django_ledger.io.roles`.
Roles serve several purposes:

1. Group accounts into common namespaces
2. Provide consistency across user-defined fields
3. Enable accurate generation of financial statements
4. Facilitate financial ratio calculations
"""
from itertools import groupby
from random import randint
from typing import Union, List, Optional
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F, UniqueConstraint
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from treebeard.mp_tree import MP_Node, MP_NodeManager, MP_NodeQuerySet

from django_ledger.io.roles import (
    ACCOUNT_ROLE_CHOICES, BS_ROLES, GROUP_INVOICE, GROUP_BILL, validate_roles,
    GROUP_ASSETS, GROUP_LIABILITIES, GROUP_CAPITAL, GROUP_INCOME, GROUP_EXPENSES, GROUP_COGS,
    ROOT_GROUP, BS_BUCKETS, ROOT_ASSETS, ROOT_LIABILITIES,
    ROOT_CAPITAL, ROOT_INCOME, ROOT_EXPENSES, ROOT_COA, VALID_PARENTS,
    ROLES_ORDER_ALL
)
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import DJANGO_LEDGER_ACCOUNT_CODE_GENERATE, DJANGO_LEDGER_ACCOUNT_CODE_USE_PREFIX

DEBIT = 'debit'
"""A constant, identifying a DEBIT Account or DEBIT transaction in the respective database fields"""

CREDIT = 'credit'
"""A constant, identifying a CREDIT Account or CREDIT transaction in the respective database fields"""


class AccountModelValidationError(ValidationError):
    pass


class AccountModelQuerySet(MP_NodeQuerySet):
    """
    Custom QuerySet for AccountModel inheriting from MP_NodeQuerySet.
    """

    def active(self):
        """
        Filters the queryset to include only active items.

        Returns
        -------
        AccountModelQuerySet
            A filtered queryset containing only the items marked as active.
        """
        return self.filter(active=True)

    def inactive(self):
        """
        Filters and returns queryset entries where the active field is set to False.

        Returns
        -------
        AccountModelQuerySet
            A queryset containing entries with active=False.
        """
        return self.filter(active=False)

    def locked(self):
        """
        Filters the queryset to include only locked AccountModels.

        Returns
        -------
        AccountModelQuerySet
            A queryset containing only the objects with locked set to True.
        """
        return self.filter(locked=True)

    def unlocked(self):
        """
        Returns a filtered list of items where the 'locked' attribute is set to False.

        Returns
        -------
        AccountModelQuerySet
            A queryset of items with 'locked' attribute set to False
        """
        return self.filter(locked=False)

    def with_roles(self, roles: Union[List, str]):
        """
        Filter the accounts based on the specified roles. This method helps to retrieve accounts associated
        with a particular role or a list of roles.

        For example, to get all accounts categorized under the role "asset_ppe_build" (which might include
        fixed assets like Buildings), you can utilize this method.

        Parameters
        ----------
        roles : Union[List[str], str]
            The role or a list of roles to filter the accounts by. If a single string is provided, it is converted
            into a list containing that role.

        Returns
        -------
        AccountModelQuerySet
            A QuerySet of accounts filtered by the provided roles.
        """
        roles = validate_roles(roles)
        if isinstance(roles, str):
            roles = [roles]
        roles = validate_roles(roles)
        return self.filter(role__in=roles)

    def with_codes(self, codes: Union[List, str]):
        if isinstance(codes, str):
            codes = [codes]
        return self.filter(code__in=codes)

    def expenses(self):
        """
        Retrieve a queryset containing expenses filtered by specified roles.

        This method filters the expenses based on roles defined in the
        `GROUP_EXPENSES` constant. It ensures that only the relevant expenses
        associated with the specified roles are included in the queryset.

        Returns
        -------
            AccountModelQuerySet
                A queryset consisting of expenses filtered according to the roles in `GROUP_EXPENSES`.
        """
        return self.filter(role__in=GROUP_EXPENSES)

    def is_coa_root(self):
        """
        Retrieves the Chart of Accounts (CoA) root node queryset.

        A Chart of Accounts Root is a foundational element indicating the primary node in the
        account hierarchy. This method filters the queryset to include only the Chart of Accounts (CoA)
        root node.

        Returns
        -------
            AccountModelQuerySet
        """
        return self.filter(role__in=ROOT_GROUP)

    def not_coa_root(self):
        """
        Exclude AccountModels with ROOT_GROUP role from the QuerySet.

        Returns
        -------
        AccountModelQuerySet
            A QuerySet excluding users with role in ROOT_GROUP.
        """
        return self.exclude(role__in=ROOT_GROUP)

    def gb_bs_role(self):
        """
        Groups accounts by Balance Sheet Bucket and then further groups them by role.

        Returns
        -------
            List[Tuple]
                A list where each element is a tuple. The first element of the tuple is the BS bucket,
                and the second element is a list of tuples where each sub-tuple contains a role display
                and a list of accounts that fall into that role within the BS bucket.
        """
        accounts_gb = list(
            (r, sorted(list(gb), key=lambda acc: ROLES_ORDER_ALL.index(acc.role))) for r, gb in
            groupby(self, key=lambda acc: acc.get_bs_bucket())
        )
        return [
            (bsr, [
                (r, sorted(list(l), key=lambda acc: acc.code)) for r, l in
                groupby(gb, key=lambda a: a.get_role_display())
            ]) for bsr, gb in accounts_gb
        ]

    def is_role_default(self):
        """
        Filter the queryset to include only entries where `role_default`
        is set to True, excluding entries marked as 'coa_root'.

        Returns
        -------
        AccountModelQuerySet
            Filtered queryset with `role_default` set to True and excluding 'coa_root' entries.
        """
        return self.not_coa_root().filter(role_default=True)

    def can_transact(self):
        """
        Filter the queryset to include only accounts that can accept new transactions.

        Returns
        -------
        QuerySet
            A QuerySet containing the filtered results.
        """
        return self.filter(
            Q(locked=False) &
            Q(active=True) &
            Q(coa_model__active=True)
        )

    def available(self):
        return self.filter(
            Q(locked=False) &
            Q(active=True) &
            Q(coa_model__active=True)
        )

    def for_bill(self):
        """
        Retrieves only available and unlocked AccountModels for a specific EntityModel,
        specifically for the creation and management of Bills. Roles within the 'GROUP_BILL'
        context include: ASSET_CA_CASH, ASSET_CA_PREPAID, and LIABILITY_CL_ACC_PAYABLE.

        Returns
        -------
        AccountModelQuerySet
            A QuerySet of the requested EntityModel's chart of accounts.
        """
        return self.available().filter(role__in=GROUP_BILL)

    def for_invoice(self):
        """
        Retrieves available and unlocked AccountModels for a specific EntityModel, specifically for the creation
        and management of Invoices.

        This method ensures that only relevant accounts are pulled, as defined under the roles in `GROUP_INVOICE`.
        These roles include: ASSET_CA_CASH, ASSET_CA_RECEIVABLES, and LIABILITY_CL_DEFERRED_REVENUE.

        Returns
        -------
        AccountModelQuerySet
            A QuerySet containing the AccountModels relevant for the specified EntityModel and the roles defined
            in `GROUP_INVOICE`.
        """
        return self.available().filter(role__in=GROUP_INVOICE)


class AccountModelManager(MP_NodeManager):
    """
    AccountModelManager class provides methods to manage and retrieve AccountModel objects.
    It inherits from MP_NodeManager for tree-like model implementation.
    """

    def get_queryset(self) -> AccountModelQuerySet:
        """
        Retrieve and return athe default AccountModel QuerySet.

        The query set is ordered by the 'path' field and uses 'select_related' to reduce the number of database queries
        by retrieving the related 'coa_model'.

        Returns
        -------
        AccountModelQuerySet
            An instance of AccountModelQuerySet ordered by 'path' and prefetching related 'coa_model'.
        """
        return AccountModelQuerySet(
            self.model,
            using=self._db
        ).order_by('path').select_related(
            'coa_model').annotate(
            _coa_slug=F('coa_model__slug'),
            _coa_active=F('coa_model__active'),
            _entity_slug=F('coa_model__entity__slug'),
        )

    def for_user(self, user_model) -> AccountModelQuerySet:
        """
        Parameters
        ----------
        user_model : UserModel
            The user model instance to use for filtering.

        Returns
        -------
        AccountModelQuerySet
            The filtered queryset based on the user's permissions. Superusers get the complete queryset whereas other
            users get a filtered queryset based on their role as admin or manager in the entity.
        """
        qs = self.get_queryset()
        if user_model.is_superuser:
            return qs
        return qs.filter(
            Q(coa_model__entity__admin=user_model) |
            Q(coa_model__entity__managers__in=[user_model])
        )

    def for_entity(
            self,
            user_model,
            entity_model,
            coa_slug: Optional[str] = None
    ) -> AccountModelQuerySet:
        """
        Retrieve accounts associated with a specified EntityModel and Chart of Accounts.

        Parameters
        ----------
        user_model : User
            The Django User instance initiating the request. Used to check for required permissions.
        entity_model : Union[EntityModel, str]
            An instance of EntityModel or its slug. This determines the entity whose accounts are being retrieved.
            A database query will be carried out to identify the default Chart of Accounts.
        coa_slug : Optional[str], default=None
            The slug for a specific Chart of Accounts to be used. If None, the default Chart of Accounts will be selected.

        Returns
        -------
        AccountModelQuerySet
            A QuerySet containing accounts associated with the specified EntityModel and Chart of Accounts.

        Raises
        ------
        AccountModelValidationError
            If the entity_model is neither an instance of EntityModel nor a string.
        """
        qs = self.for_user(user_model)
        EntityModel = lazy_loader.get_entity_model()

        if isinstance(entity_model, EntityModel):
            entity_model = entity_model
            qs = qs.filter(coa_model__entity=entity_model)
        elif isinstance(entity_model, str):
            qs = qs.filter(coa_model__entity__slug__exact=entity_model)
        else:
            raise AccountModelValidationError(
                message='Must pass an instance of EntityModel or String for entity_slug.'
            )

        return qs.filter(
            coa_model__slug__exact=coa_slug
        ) if coa_slug else qs.filter(
            coa_model__slug__exact=F('coa_model__entity__default_coa__slug')
        )


def account_code_validator(value: str):
    if not value.isalnum():
        raise AccountModelValidationError(_('Account code must be alpha numeric, got {%s}') % value)


class AccountModelAbstract(MP_Node, CreateUpdateMixIn):
    """
    Abstract class representing an Account Model.

    Attributes
    ----------
    BALANCE_TYPE : list
        List of choices for the balance type of the account. Options include 'Credit' and 'Debit'.
    uuid : UUIDField
        Unique identifier for each account instance.
    code : CharField
        Code representing the account, constrained by length and specific validation rules.
    name : CharField
        Name of the account, constrained by length.
    role : CharField
        Role associated with the account, with specific predefined choices.
    role_default : BooleanField
        Flag indicating if this account is the default for its role.
    balance_type : CharField
        Type of balance the account holds, must be either 'debit' or 'credit'.
    locked : BooleanField
        Indicates whether the account is locked.
    active : BooleanField
        Indicates whether the account is active.
    coa_model : ForeignKey
        Reference to the associated ChartOfAccountModel.
    """

    BALANCE_TYPE = [
        (CREDIT, _('Credit')),
        (DEBIT, _('Debit'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    code = models.CharField(max_length=10, verbose_name=_('Account Code'), validators=[account_code_validator])
    name = models.CharField(max_length=100, verbose_name=_('Account Name'))
    role = models.CharField(max_length=30, choices=ACCOUNT_ROLE_CHOICES, verbose_name=_('Account Role'))
    role_default = models.BooleanField(null=True, blank=True, verbose_name=_('Coa Role Default Account'))
    balance_type = models.CharField(max_length=6, choices=BALANCE_TYPE, verbose_name=_('Account Balance Type'))
    locked = models.BooleanField(default=False, verbose_name=_('Locked'))
    active = models.BooleanField(default=False, verbose_name=_('Active'))
    coa_model = models.ForeignKey('django_ledger.ChartOfAccountModel',
                                  on_delete=models.CASCADE,
                                  verbose_name=_('Chart of Accounts'))
    objects = AccountModelManager()
    node_order_by = ['uuid']

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        constraints = [
            UniqueConstraint(
                fields=('coa_model', 'code'),
                name='unique_code_for_coa_model',
                violation_error_message=_('Account codes must be unique for each Chart of Accounts Model.')
            ),
            UniqueConstraint(
                fields=('coa_model', 'role', 'role_default'),
                name='only_one_account_assigned_as_default_for_role',
                violation_error_message=_('Only one default account for role permitted.')
            )
        ]
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['balance_type']),
            models.Index(fields=['active']),
            models.Index(fields=['locked']),
            models.Index(fields=['coa_model', 'code']),
            models.Index(fields=['code'])
        ]

    def __str__(self):
        return '{x1} - {x5}: {x2} ({x3}/{x4})'.format(
            x1=self.role_bs.upper(),
            x2=self.name,
            x3=self.role.upper(),
            x4=self.balance_type,
            x5=self.code
        )

    @property
    def coa_slug(self):
        try:
            return getattr(self, '_coa_slug')
        except AttributeError:
            return self.coa_model.slug

    @property
    def entity_slug(self):
        return getattr(self, '_entity_slug')

    @classmethod
    def create_account(cls,
                       name: str,
                       role: bool,
                       balance_type: str,
                       is_role_default: bool = False,
                       locked: bool = False,
                       active: bool = False,
                       **kwargs):
        """
        Create a new AccountModel instance, managing parent/child relationships properly.

        This convenience method ensures correct creation of new accounts, handling the intricate logic needed for
        maintaining hierarchical relationships between accounts.

        Parameters
        ----------
        name : str
            Name of the new account entity.
        role : str
            Role assigned to the account.
        balance_type : str
            Type of balance associated with the account. Must be either 'debit' or 'credit'.
        is_role_default : bool, optional
            Indicates if the account should be the default for its role. Only one default account per role is allowed.
            Defaults to False.
        locked : bool, optional
            Flags the account as locked. Defaults to False.
        active : bool, optional
            Flags the account as active. Defaults to True.
        **kwargs : dict, optional
            Additional attributes for account creation.

        Returns
        -------
        AccountModel
            The newly created `AccountModel` instance.
        """
        account_model = cls(
            name=name,
            role=role,
            balance_type=balance_type,
            role_default=is_role_default,
            locked=locked,
            active=active,
            **kwargs
        )
        account_model.clean()
        account_model = cls.add_root(instance=account_model)
        return account_model

    @property
    def role_bs(self) -> str:
        """
        Returns the principal role of the account on the balance sheet.

        The principal role can be one of the following:
        - 'asset'
        - 'liability'
        - 'equity'

        Returns
        -------
        str
            A string representing the principal role of the account on the balance sheet.
        """
        return BS_ROLES.get(self.role)

    def is_root_account(self):
        """
        Checks if the current user's role belongs to the ROOT_GROUP.

        Returns
        -------
        bool
            True if the role is in the ROOT_GROUP, False otherwise
        """
        return self.role in ROOT_GROUP

    def is_debit(self) -> bool:
        """
        Checks if the account has a DEBIT balance type.

        Returns
        -------
        bool
            True if account has a DEBIT balance, else False.
        """
        return self.balance_type == DEBIT

    def is_credit(self):
        """
        Checks if the Account Model has a CREDIT balance type.

        Returns
        -------
        bool
            True if account has a CREDIT balance, else False.
        """
        return self.balance_type == CREDIT

    def is_coa_root(self):
        """
        Check if the current Account Model role is 'ROOT_COA'.

        Returns
        -------
        bool
            True if the role is 'ROOT_COA', False otherwise.
        """
        return self.role == ROOT_COA

    def is_asset(self) -> bool:
        """
        Determines if the current Account Model role of the instance is considered an asset.

        Returns
        -------
        bool
            True if the role is part of the GROUP_ASSETS, False otherwise.
        """
        return self.role in GROUP_ASSETS

    def is_liability(self) -> bool:
        """
        Determines if the current Account Model role is considered a liability.

        Returns
        -------
        bool
            True if the role is part of GROUP_LIABILITIES, otherwise False.
        """
        return self.role in GROUP_LIABILITIES

    def is_capital(self) -> bool:
        """
        Checks if the current Account Model role is in the capital group.

        Returns
        -------
        bool
            True if the role is in GROUP_CAPITAL, otherwise False.
        """
        return self.role in GROUP_CAPITAL

    def is_income(self) -> bool:
        """
        Determines whether the current Account Model role belongs to the income group.

        Parameters
        ----------
        self : object
            The instance of the class containing attribute 'role'.

        Returns
        -------
        bool
            True if the role is in the GROUP_INCOME list, False otherwise.
        """
        return self.role in GROUP_INCOME

    def is_cogs(self) -> bool:
        """
        Determines if the role of the object is part of the GROUP_COGS.

        Returns
        -------
        bool
            True if the object's role is part of the GROUP_COGS, False otherwise.
        """
        return self.role in GROUP_COGS

    def is_expense(self) -> bool:
        """
        Checks if the current Account Model `role` is categorized under `GROUP_EXPENSES`.

        Parameters
        ----------
        None

        Returns
        -------
        bool
            True if `role` is in `GROUP_EXPENSES`, otherwise False.
        """
        return self.role in GROUP_EXPENSES

    def is_active(self) -> bool:
        """
        Determines if the current instance is active.

        Returns
        -------
        bool
            True if the instance is active, otherwise False
        """
        return self.active is True

    def is_locked(self) -> bool:
        """
        Determines if the current object is locked.

        Returns
        -------
        bool
            True if the object is locked, False otherwise.

        """
        return self.locked is True

    def is_coa_active(self) -> bool:
        try:
            return getattr(self, '_coa_active')
        except AttributeError:
            pass
        return self.coa_model.active

    def can_activate(self):
        """
        Determines if the object can be activated.

        Returns
        -------
        bool
            True if the object is inactive, otherwise False.
        """
        return all([
            self.active is False
        ])

    def can_deactivate(self):
        """
        Determine if the object can be deactivated.

        Checks if the `active` attribute is set to `True`.

        Returns
        -------
        bool
            True if the object is currently active and can be deactivated, otherwise False.
        """
        return all([
            self.active is True
        ])

    def can_lock(self):
        return all([
            self.locked is False
        ])

    def can_unlock(self):
        return all([
            self.locked is True
        ])

    def lock(self, commit: bool = True, raise_exception: bool = True, **kwargs):
        if not self.can_lock():
            if raise_exception:
                raise AccountModelValidationError(
                    message=_(f'Cannot lock account {self.code}: {self.name}. Active: {self.is_active()}')
                )
            return

        self.locked = True
        if commit:
            self.save(update_fields=[
                'locked',
                'updated'
            ])

    def unlock(self, commit: bool = True, raise_exception: bool = True, **kwargs):
        if not self.can_unlock():
            if raise_exception:
                raise AccountModelValidationError(
                    message=_(f'Cannot unlock account {self.code}: {self.name}. Active: {self.is_active()}')
                )
            return

        self.locked = False
        if commit:
            self.save(update_fields=[
                'locked',
                'updated'
            ])

    def activate(self, commit: bool = True, raise_exception: bool = True, **kwargs):
        """
        Checks if the Account Model instance can be activated, then Activates the AccountModel instance.
        Raises exception if AccountModel cannot be activated.

        Parameters
        ----------
        commit : bool, optional
            If True, commit the changes to the database by calling the save method.
        raise_exception : bool, optional
            If True, raises an AccountModelValidationError if the account cannot be activated.
        kwargs : dict
            Additional parameters that can be passed for further customization.
        """
        if not self.can_activate():
            if raise_exception:
                raise AccountModelValidationError(
                    message=_(f'Cannot activate account {self.code}: {self.name}. Active: {self.is_active()}')
                )
            return
        self.active = True
        if commit:
            self.save(update_fields=[
                'active',
                'updated'
            ])

    def deactivate(self, commit: bool = True, raise_exception: bool = True, **kwargs):
        """
        Checks if the Account Model instance can be de-activated, then De-activates the AccountModel instance.
        Raises exception if AccountModel cannot be de-activated.

        Parameters
        ----------
        commit : bool, optional
            If True, commit the changes to the database by calling the save method.
        raise_exception : bool, optional
            If True, raises an AccountModelValidationError if the account cannot be activated.
        kwargs : dict
            Additional parameters that can be passed for further customization.
        """
        if not self.can_deactivate():
            if raise_exception:
                raise AccountModelValidationError(
                    message=_(f'Cannot deactivate account {self.code}: {self.name}. Active: {self.is_active()}')
                )
            return
        self.active = False
        if commit:
            self.save(
                update_fields=[
                    'active',
                    'updated'
                ])

    def can_transact(self) -> bool:
        """
        Determines if a transaction can be performed based on multiple conditions.

        Returns
        -------
        bool
            True if all conditions are met, enabling a transaction; False otherwise.

        Conditions:
        1. The chart of accounts (coa_model) must be active.
        2. The entity must not be locked.
        3. The entity itself must be active.
        """
        return all([
            self.is_coa_active(),
            not self.is_locked()
        ])

    def get_code_prefix(self) -> str:
        """
        Returns the code prefix based on the account type.

        This method determines the account type by calling the respective
        account type methods and returns the corresponding code prefix based on Accounting best practices..

        Returns
        -------
        str
            The code prefix for the account type. The possible values are:
            '1' for assets, '2' for liabilities, '3' for capital,
            '4' for income, '5' for cost of goods sold (COGS),
            '6' for expenses.

        Raises
        ------
        AccountModelValidationError
            If the account role does not match any of the predefined categories.
        """
        if self.is_asset():
            return '1'
        elif self.is_liability():
            return '2'
        elif self.is_capital():
            return '3'
        elif self.is_income():
            return '4'
        elif self.is_cogs():
            return '5'
        elif self.is_expense():
            return '6'
        raise AccountModelValidationError(f'Invalid role match for role {self.role}...')

    def get_root_role(self) -> str:
        """
        Returns the root role corresponding to the account type.

        Returns
        -------
        str
            The root role corresponding to the account type.

        Raises
        ------
        AccountModelValidationError
            If no valid role match is found for the account's role.
        """
        if self.is_asset():
            return ROOT_ASSETS
        elif self.is_liability():
            return ROOT_LIABILITIES
        elif self.is_capital():
            return ROOT_CAPITAL
        elif self.is_income():
            return ROOT_INCOME
        elif self.is_cogs():
            return ROOT_GROUP
        elif self.is_expense():
            return ROOT_EXPENSES
        elif self.is_coa_root():
            return ROOT_COA
        raise AccountModelValidationError(f'Invalid role match for role {self.role}...')

    def get_account_move_choice_queryset(self):
        """
        Retrieves a filtered queryset of account models that the current Account Model instance
        can be a child of.

        The queryset is filtered based on the specified role and its hierarchical parent roles.
        Account models with a UUID matching the current instance's UUID are excluded from the results.

        Returns
        -------
        QuerySet
            A filtered set of account models suitable for moving the current instance under.
        """
        return self.coa_model.accountmodel_set.filter(
            role__in=[
                self.role,
                self.get_root_role(),
                *VALID_PARENTS.get(self.role, [])
            ],
        ).exclude(uuid__exact=self.uuid)

    def get_bs_bucket(self) -> str:
        return BS_BUCKETS[self.get_code_prefix()]

    def is_indented(self):
        """
        Check if the current depth level is greater than 2.

        Returns
        -------
        bool
            True if the depth is greater than 2, False otherwise.
        """
        return self.depth > 2

    def get_html_pixel_indent(self):
        """
        Calculates the pixel indentation for HTML elements based on the depth attribute for UI purposes

        Returns
        -------
        str
            The calculated pixel indentation as a string with 'px' suffix.
        """
        return f'{(self.depth - 2) * 40}px'

    def generate_random_code(self):
        """
        Generates a random code for the account adding a prefix 1-6 depending on account role.

        Raises
        ------
        AccountModelValidationError
            If the account role is not assigned before code generation.

        Returns
        -------
        str
            A randomly generated code prefixed with a role-based prefix.
        """
        if not self.role:
            raise AccountModelValidationError('Must assign account role before generate random code')

        prefix = self.get_code_prefix()
        ri = randint(10000, 99999)
        return f'{prefix}{ri}'

    # URLS...
    def get_absolute_url(self) -> str:
        return reverse(
            viewname='django_ledger:account-detail',
            kwargs={
                'account_pk': self.uuid,
                'entity_slug': self.entity_slug,
                'coa_slug': self.coa_slug
            }
        )

    def get_update_url(self) -> str:
        return reverse(
            viewname='django_ledger:account-update',
            kwargs={
                'account_pk': self.uuid,
                'entity_slug': self.entity_slug,
                'coa_slug': self.coa_slug
            }
        )

    def get_action_deactivate_url(self) -> str:
        return reverse(
            viewname='django_ledger:account-action-deactivate',
            kwargs={
                'account_pk': self.uuid,
                'entity_slug': self.entity_slug,
                'coa_slug': self.coa_slug
            }
        )

    def get_action_activate_url(self) -> str:
        return reverse(
            viewname='django_ledger:account-action-activate',
            kwargs={
                'account_pk': self.uuid,
                'entity_slug': self.entity_slug,
                'coa_slug': self.coa_slug
            }
        )

    def get_action_lock_url(self) -> str:
        return reverse(
            viewname='django_ledger:account-action-lock',
            kwargs={
                'account_pk': self.uuid,
                'entity_slug': self.entity_slug,
                'coa_slug': self.coa_slug
            }
        )

    def get_action_unlock_url(self) -> str:
        return reverse(
            viewname='django_ledger:account-action-unlock',
            kwargs={
                'account_pk': self.uuid,
                'entity_slug': self.entity_slug,
                'coa_slug': self.coa_slug
            }
        )

    def get_coa_account_list_url(self) -> str:
        return reverse(
            viewname='django_ledger:account-list',
            kwargs={
                'entity_slug': self.entity_slug,
                'coa_slug': self.coa_slug
            })

    def clean(self):
        if not self.code and DJANGO_LEDGER_ACCOUNT_CODE_GENERATE:
            self.code = self.generate_random_code()

        if DJANGO_LEDGER_ACCOUNT_CODE_USE_PREFIX:
            pf = self.get_code_prefix()
            if self.code[0] != pf:
                raise AccountModelValidationError(f'Account {self.get_role_display()} code {self.code} '
                                                  f'must start with {pf} for CoA consistency')


class AccountModel(AccountModelAbstract):
    """
    Base Account Model from Account Model Abstract Class
    """

    class Meta(AccountModelAbstract.Meta):
        swappable = 'DJANGO_LEDGER_ACCOUNT_MODEL'
        abstract = False


def accountmodel_presave(instance: AccountModel, **kwargs):
    if instance.role_default is False:
        instance.role_default = None


pre_save.connect(receiver=accountmodel_presave, sender=AccountModel)
