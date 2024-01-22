"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
    * Pranav P Tulshyan <ptulshyan77@gmail.com>

The AccountModel groups and sorts transactions involving the company's assets, liabilities and equities.
Per accounting principles, an Account must be either a DEBIT-type  balance account or a CREDIT-type balance account,
depending on its purpose.

The AccountModel plays a major role when creating Journal Entries in a double entry accounting systems where
a DEBIT to a DEBIT-type AccountModel will increase its balance, and a CREDIT to a DEBIT-type AccountModel will
reduce its balance. Conversely, a CREDIT to a CREDIT-type AccountModel will increase its balance, and a
DEBIT to a CREDIT-type AccountModel will reduce its balance.

It is entirely up to the user to adopt the chart of accounts that best suits the EntityModel.
The user may choose to use the default Chart of Accounts provided by Django Ledger when creating a new EntityModel.

In Django Ledger, all account models must be assigned a role from
:func:`ACCOUNT_ROLES <django_ledger.io.roles.ACCOUNT_ROLES>`. Roles are a way to group accounts to a common namespace,
regardless of its user-defined fields. Roles are an integral part to Django Ledger since they are critical when
requesting and producing financial statements and financial ratio calculations.

AccountModels may also contain parent/child relationships as implemented by the Django Treebeard functionality.
"""
from itertools import groupby
from random import randint
from typing import Union, List, Optional
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from treebeard.mp_tree import MP_Node, MP_NodeManager, MP_NodeQuerySet

from django_ledger.io.io_core import get_localdate
from django_ledger.io.roles import (ACCOUNT_ROLE_CHOICES, BS_ROLES, GROUP_INVOICE, GROUP_BILL, validate_roles,
                                    GROUP_ASSETS,
                                    GROUP_LIABILITIES, GROUP_CAPITAL, GROUP_INCOME, GROUP_EXPENSES, GROUP_COGS,
                                    ROOT_GROUP, BS_BUCKETS, ROOT_ASSETS, ROOT_LIABILITIES,
                                    ROOT_CAPITAL, ROOT_INCOME, ROOT_EXPENSES, ROOT_COA)
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
    A custom defined QuerySet, which inherits from the Materialized Path Tree implementation
    of Django Treebeard for tree-like model implementation.
    """

    def active(self):
        """
        Active accounts which can be used to create new transactions that show on drop-down menus and forms.

        Returns
        _______
        AccountModelQuerySet
            A filtered AccountModelQuerySet of active accounts.
        """
        return self.filter(active=True)

    def inactive(self):
        """
        Inactive accounts cannot be used to create new transactions and don't show on drop-down menus and forms.

        Returns
        _______
        AccountModelQuerySet
            A filtered AccountModelQuerySet of inactive accounts.
        """
        return self.filter(active=False)

    def with_roles(self, roles: Union[List, str]):
        """
        This method is used to make query of accounts with a certain role. For instance, the fixed assets like
        Buildings have all been assigned the role of  "asset_ppe_build" role is basically an aggregation of the
        accounts under a similar category. So, to query the list of all accounts under the role "asset_ppe_build",
        we can use this function.

        Parameters
        __________
        roles: list or str
            Function accepts a single str instance of a role or a list of roles. For a list of roles , refer io.roles.py

        Returns
        _______
        AccountModelQuerySet
            Returns a QuerySet filtered by user-provided list of Roles.
        """
        if isinstance(roles, str):
            roles = [roles]
        roles = validate_roles(roles)
        return self.filter(role__in=roles)

    def expenses(self):
        return self.filter(role__in=GROUP_EXPENSES)

    def is_coa_root(self):
        return self.filter(role__in=ROOT_GROUP)

    def not_coa_root(self):
        return self.exclude(role__in=ROOT_GROUP)

    def for_entity(self, entity_slug, user_model):
        if isinstance(self, lazy_loader.get_entity_model()):
            return self.filter(
                Q(coa_model__entity=entity_slug) &
                (
                        Q(coa_model__entity__admin=user_model) |
                        Q(coa_model__entity__managers__in=[user_model])
                )
            ).order_by('code')
        return self.filter(
            Q(coa_model__entity__slug__exact=entity_slug) &
            (
                    Q(coa_model__entity__admin=user_model) |
                    Q(coa_model__entity__managers__in=[user_model])
            )
        ).order_by('code')

    def gb_bs_role(self):
        accounts_gb = list((r, list(gb)) for r, gb in groupby(self, key=lambda acc: acc.get_bs_bucket()))
        return [
            (bsr, [
                (r, list(l)) for r, l in groupby(gb, key=lambda a: a.get_role_display())
            ]) for bsr, gb in accounts_gb
        ]

    def is_role_default(self):
        return self.not_coa_root().filter(role_default=True)


class AccountModelManager(MP_NodeManager):
    """
    This Model Manager will be used as interface through which the database query operations can be provided to the
    Account Model. It uses the custom defined AccountModelQuerySet and hence overrides the normal get_queryset
    function which return all rows of a model.
    """

    def get_queryset(self) -> AccountModelQuerySet:
        """
        Sets the custom queryset as the default.
        """
        return AccountModelQuerySet(self.model).order_by('path')

    def for_user(self, user_model):
        qs = self.get_queryset()
        if user_model.is_superuser:
            return qs

    # todo: search for uses and pass EntityModel whenever possible.
    def for_entity(self,
                   user_model,
                   entity_slug,
                   coa_slug: Optional[str] = None,
                   select_coa_model: bool = True) -> AccountModelQuerySet:
        """
        Ensures that only accounts associated with the given EntityModel are returned.

        Parameters
        ----------
        entity_slug: EntityModel or str
            The EntityModel or EntityModel slug to pull accounts from. If slug is passed and coa_slug is None will
            result in an additional Database query to determine the default code of accounts.
        coa_slug: str
            Explicitly specify which chart of accounts to use. If None, will pull default Chart of Accounts.
            Discussed in detail in the CoA Model CoA slug,  basically helps in identifying the complete Chart of
            Accounts for a particular EntityModel.
        user_model:
            The Django User Model making the request to check for permissions.
        select_coa_model: bool
            Pre fetches the CoA Model information in the QuerySet. Defaults to True.

        Returns
        -------
        AccountModelQuerySet
            A QuerySet of all requested EntityModel Chart of Accounts.
        """
        qs = self.for_user(user_model)
        if select_coa_model:
            qs = qs.select_related('coa_model')

        EntityModel = lazy_loader.get_entity_model()
        if isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
            qs = qs.filter(coa_model__entity=entity_model)
        elif isinstance(entity_slug, str):
            qs = qs.filter(coa_model__entity__slug__exact=entity_slug)
        else:
            raise AccountModelValidationError(message='Must pass an instance of EntityModel or String for entity_slug.')

        if coa_slug:
            qs = qs.filter(coa_model__slug__exact=coa_slug)
        return qs.order_by('coa_model')

    def for_entity_available(self, user_model, entity_slug, coa_slug: Optional[str] = None) -> AccountModelQuerySet:
        """
        Convenience method to pull only available and unlocked AccountModels for a specific EntityModel.

        Parameters
        ----------
        entity_slug: EntityModel or str
            The EntityModel or EntityModel slug to pull accounts from. If slug is passed and coa_slug is None will
            result in an additional Database query to determine the default code of accounts.

        coa_slug: str
            Explicitly specify which chart of accounts to use. If None, will pull default Chart of Accounts.
            Discussed in detail in the CoA Model CoA slug,  basically helps in identifying the complete Chart of
            Accounts for a particular EntityModel.

        user_model:
            The Django User Model making the request to check for permissions.

        Returns
        -------
        AccountModelQuerySet
            A QuerySet of all requested EntityModel Chart of Accounts.
        """
        qs = self.for_entity(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(
            active=True,
            locked=False
        )

    def with_roles(self, roles: Union[list, str], entity_slug, user_model) -> AccountModelQuerySet:
        """
        This method is used to make query of accounts with a certain role. For instance, the fixed assets like
        Buildings have all been assigned the role of  "asset_ppe_build" role is basically an aggregation of the
        accounts under a similar category. So, to query the list of all accounts under the role "asset_ppe_build",
        we can use this function.

        Parameters
        ----------
        entity_slug: EntityModel or str
            The EntityModel or EntityModel slug to pull accounts from. If slug is passed and coa_slug is None will
            result in an additional Database query to determine the default code of accounts.
        user_model
            The Django User Model making the request to check for permissions.
        roles: list or str
            Function accepts a single str instance of a role or a list of roles. For a list of roles , refer io.roles.py
        Returns
        -------
        AccountModelQuerySet
            Returns a QuerySet filtered by user-provided list of Roles.
        """
        roles = validate_roles(roles)
        if isinstance(roles, str):
            roles = [roles]
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(role__in=roles)

    def with_roles_available(self, roles: Union[list, str],
                             entity_slug,
                             user_model,
                             coa_slug: Optional[str]) -> AccountModelQuerySet:
        """
        Convenience method to pull only available and unlocked AccountModels for a specific EntityModel and for a
        specific list of roles.

        Parameters
        ----------
        entity_slug: EntityModel or str
            The EntityModel or EntityModel slug to pull accounts from. If slug is passed and coa_slug is None will
            result in an additional Database query to determine the default code of accounts.
        coa_slug: str
            Explicitly specify which chart of accounts to use. If None, will pull default Chart of Accounts.
            Discussed in detail in the CoA Model CoA slug,  basically helps in identifying the complete Chart of
            Accounts for a particular EntityModel.
        user_model:
            The Django User Model making the request to check for permissions.
        roles: list or str
            Function accepts a single str instance of a role or a list of roles. For a list of roles , refer io.roles.py

        Returns
        -------
        AccountModelQuerySet
            A QuerySet of all requested EntityModel Chart of Accounts.
        """

        if isinstance(roles, str):
            roles = [roles]
        roles = validate_roles(roles)
        qs = self.for_entity_available(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(role__in=roles)

    def coa_roots(self, user_model, entity_slug, coa_slug) -> AccountModelQuerySet:
        """
        Fetches the Code of Account Root Accounts.

        Parameters
        ----------
        entity_slug: EntityModel or str
            The EntityModel or EntityModel slug to pull accounts from. If slug is passed and coa_slug is None will
            result in an additional Database query to determine the default code of accounts.
        coa_slug: str
            Explicitly specify which chart of accounts to use. If None, will pull default Chart of Accounts.
            Discussed in detail in the CoA Model CoA slug,  basically helps in identifying the complete Chart of
            Accounts for a particular EntityModel.
        user_model:
            The Django User Model making the request to check for permissions.

        Returns
        -------

        """
        qs = self.for_entity(user_model=user_model, entity_slug=entity_slug, coa_slug=coa_slug)
        return qs.is_coa_root()

    def for_invoice(self, user_model, entity_slug: str, coa_slug: Optional[str] = None) -> AccountModelQuerySet:
        """
        Convenience method to pull only available and unlocked AccountModels for a specific EntityModel relevant only
        for creating and management of Invoices. See :func:`GROUP_INVOICE <django_ledger.io.roles.GROUP_INVOICE>`.

        Roles in GROUP_INVOICE: ASSET_CA_CASH, ASSET_CA_RECEIVABLES, LIABILITY_CL_DEFERRED_REVENUE.

        Parameters
        __________

        entity_slug: EntityModel or str
            The EntityModel or EntityModel slug to pull accounts from. If slug is passed and coa_slug is None will
            result in an additional Database query to determine the default code of accounts.

        coa_slug: str
            Explicitly specify which chart of accounts to use. If None, will pull default Chart of Accounts.
            Discussed in detail in the CoA Model CoA slug,  basically helps in identifying the complete Chart of
            Accounts for a particular EntityModel.

        user_model:
            The Django User Model making the request to check for permissions.

        Returns
        _______
        AccountModelQuerySet
            A QuerySet of all requested EntityModel Chart of Accounts.
        """
        qs = self.for_entity_available(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(role__in=GROUP_INVOICE)

    def for_bill(self, user_model, entity_slug, coa_slug: Optional[str] = None) -> AccountModelQuerySet:
        """
        Convenience method to pull only available and unlocked AccountModels for a specific EntityModel relevant only
        for creating and management of Bills. See :func:`GROUP_BILL <django_ledger.io.roles.GROUP_BILL>`.

        Roles in GROUP_BILL: ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_ACC_PAYABLE.

        Parameters
        __________

        entity_slug: EntityModel or str
            The EntityModel or EntityModel slug to pull accounts from. If slug is passed and coa_slug is None will
            result in an additional Database query to determine the default code of accounts.

        coa_slug: str
            Explicitly specify which chart of accounts to use. If None, will pull default Chart of Accounts.
            Discussed in detail in the CoA Model CoA slug,  basically helps in identifying the complete Chart of
            Accounts for a particular EntityModel.

        user_model:
            The Django User Model making the request to check for permissions.

        Returns
        _______
        AccountModelQuerySet
            A QuerySet of all requested EntityModel Chart of Accounts.
        """
        qs = self.for_entity_available(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(role__in=GROUP_BILL)


def account_code_validator(value: str):
    if not value.isalnum():
        raise AccountModelValidationError(_('Account code must be alpha numeric, got {%s}') % value)


class AccountModelAbstract(MP_Node, CreateUpdateMixIn):
    """
    Django Ledger Base Account Model Abstract. This is the main abstract class which the Account Model database will
    inherit, and it contains the fields/columns/attributes which the said ledger table will have. In addition to the
    attributes mentioned below, it also has the fields/columns/attributes mentioned in the ParentChileMixin & the
    CreateUpdateMixIn. Read about these mixin here.

    Below are the fields specific to the accounts model.

    Attributes
    ----------
    uuid: UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().

    code: str
        Each account will have its own alphanumeric code.
        For example:
        * Cash Account -> Code 1010.
        * Inventory -> 1200.
        * Maximum Length allowed is 10.

    name: str
        This is the user defined name  of the Account. the maximum length for Name of the ledger allowed is 100

    role: str
        Each Account needs to be assigned a certain Role. The exhaustive list of ROLES is defined in io.roles.

    balance_type: str
        Each account will have a default Account type i.e. Either Debit or Credit.
        For example:
        * Assets like Cash, Inventory, Accounts Receivable or Expenses like Rent, Salary will have balance_type=DEBIT.
        * Liabilities, Equities and Income like Payables, Loans, Income, Sales, Reserves will have balance_type=CREDIT.

    locked: bool
        This determines whether any transactions can be added in the account. Before making any update to the
        account, the account needs to be unlocked. Default value is set to False i.e. Unlocked.

    active: bool
        Determines whether the concerned account is active. Any Account can be used only when it is unlocked and
        Active. Default value is set to True.

    coa_model: ChartOfAccountsModel
        Each Accounts must be assigned a ChartOfAccountsModel. By default, one CoA will be created for each entity.
        However, the creating of a new AccountModel must have an explicit assignment of a ChartOfAccountModel.
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
                                  editable=False,
                                  verbose_name=_('Chart of Accounts'))
    objects = AccountModelManager()
    node_order_by = ['uuid']

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        unique_together = [
            ('coa_model', 'code'),
            ('coa_model', 'role', 'role_default')
        ]
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['balance_type']),
            models.Index(fields=['active']),
            models.Index(fields=['locked']),
            models.Index(fields=['coa_model'])
        ]

    def __str__(self):
        return '{x1} - {x5}: {x2} ({x3}/{x4})'.format(
            x1=self.role_bs.upper(),
            x2=self.name,
            x3=self.role.upper(),
            x4=self.balance_type,
            x5=self.code
        )

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
        Convenience Method to Create a new Account Model. This is the preferred method to create new Accounts in order
        to properly handle parent/child relationships between models.

        Parameters
        ----------
        name: str
            The name of the new Entity.
        role: str
            Account role.
        balance_type: str
            Account Balance Type. Must be 'debit' or 'credit'.
        is_role_default: bool
            If True, assigns account as default for role. Only once default account per role is permitted.
        locked: bool
            Marks account as Locked. Defaults to False.
        active: bool
            Marks account as Active. Defaults to True.


        Returns
        -------
        AccountModel
            The newly created AccountModel instance.

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
        The principal role of the account on the balance sheet.
        Options are:
        * asset
        * liability
        * equity

        Returns
        -------
        str
            A String representing the principal role of the account on the balance sheet.
        """
        return BS_ROLES.get(self.role)

    def is_root_account(self):
        return self.role in ROOT_GROUP

    def is_debit(self) -> bool:
        """
        Checks if the account has a DEBIT balance.
        Returns
        -------
        bool
            True if account has a DEBIT balance, else False.
        """
        return self.balance_type == DEBIT

    def is_credit(self):
        """
        Checks if the account has a CREDIT balance.
        Returns
        -------
        bool
            True if account has a CREDIT balance, else False.
        """
        return self.balance_type == CREDIT

    def is_coa_root(self):
        return self.role in ROOT_GROUP

    def is_asset(self) -> bool:
        return self.role in GROUP_ASSETS

    def is_liability(self) -> bool:
        return self.role in GROUP_LIABILITIES

    def is_capital(self) -> bool:
        return self.role in GROUP_CAPITAL

    def is_income(self) -> bool:
        return self.role in GROUP_INCOME

    def is_cogs(self) -> bool:
        return self.role in GROUP_COGS

    def is_expense(self) -> bool:
        return self.role in GROUP_EXPENSES

    def is_active(self) -> bool:
        return self.active is True

    def can_activate(self):
        return all([
            self.active is False
        ])

    def can_deactivate(self):
        return all([
            self.active is True
        ])

    def activate(self, commit: bool = True, raise_exception: bool = True, **kwargs):
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
        if not self.can_deactivate():
            if raise_exception:
                raise AccountModelValidationError(
                    message=_(f'Cannot deactivate account {self.code}: {self.name}. Active: {self.is_active()}')
                )
            return
        self.active = False
        if commit:
            self.save(update_fields=[
                'active',
                'updated'
            ])

    def get_code_prefix(self) -> str:

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
        elif self.is_coa_root():
            return '0'
        else:
            raise AccountModelValidationError(f'Invalid role match for role {self.role}...')

    def get_root_role(self) -> str:
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
        else:
            raise AccountModelValidationError(f'Invalid role match for role {self.role}...')

    def get_account_move_choice_queryset(self):
        return self.coa_model.accountmodel_set.filter(
            role__in=[
                self.role,
                self.get_root_role()
            ],
        ).exclude(uuid__exact=self.uuid)

    def get_bs_bucket(self) -> str:
        return BS_BUCKETS[self.get_code_prefix()]

    def is_indented(self):
        return self.depth > 2

    def get_html_pixel_indent(self):
        return f'{(self.depth - 2) * 40}px'

    def generate_random_code(self):
        if not self.role:
            raise AccountModelValidationError('Must assign account role before generate random code')

        prefix = self.get_code_prefix()
        ri = randint(10000, 99999)
        return f'{prefix}{ri}'

    def get_absolute_url(self):
        return reverse(
            viewname='django_ledger:account-detail-year',
            kwargs={
                'account_pk': self.uuid,
                'entity_slug': self.coa_model.entity.slug,
                'year': get_localdate().year
            }
        )

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


def accountmodel_presave(instance: AccountModel, **kwargs):
    if instance.role_default is False:
        instance.role_default = None


pre_save.connect(receiver=accountmodel_presave, sender=AccountModel)
