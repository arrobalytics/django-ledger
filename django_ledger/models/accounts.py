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

from typing import Union, List, Optional
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from treebeard.mp_tree import MP_Node, MP_NodeManager, MP_NodeQuerySet

from django_ledger.io.roles import ACCOUNT_ROLES, BS_ROLES, GROUP_INVOICE, GROUP_BILL, validate_roles
from django_ledger.models import lazy_loader
from django_ledger.models.mixins import CreateUpdateMixIn

DEBIT = 'debit'
"""A constant, identifying a DEBIT Account or DEBIT transaction in the respective database fields"""

CREDIT = 'credit'
"""A constant, identifying a CREDIT Account or CREDIT transaction in the respective database fields"""


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

    # todo: search for uses and pass EntityModel whenever possible.
    def for_entity(self, user_model, entity_slug, coa_slug: Optional[str] = None) -> AccountModelQuerySet:
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

        Returns
        -------
        AccountModelQuerySet
            A QuerySet of all requested EntityModel Chart of Accounts.
        """
        qs = self.get_queryset()
        EntityModel = lazy_loader.get_entity_model()
        if isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
            slug = entity_slug.slug
        else:
            slug = entity_slug
            entity_model = EntityModel.objects.get(slug__exact=slug)

        qs = qs.filter(
            Q(coa_model__entity=entity_model) &
            (
                    Q(coa_model__entity__admin=user_model) |
                    Q(coa_model__entity__managers__in=[user_model])
            )
        ).order_by('code')

        if coa_slug:
            return qs.filter(coa_model___slug__exact=coa_slug)
        return qs.filter(coa_model__uuid__exact=entity_model.default_coa_id)

    def for_entity_available(self, user_model, entity_slug, coa_slug: Optional[str] = None) -> AccountModelQuerySet:
        """
        Convenience method to pull only available and unlocked AccountModels for a specific EntityModel.

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
        __________
        roles: list or str
            Function accepts a single str instance of a role or a list of roles. For a list of roles , refer io.roles.py

        Returns
        _______
        AccountModelQuerySet
            Returns a QuerySet filtered by user-provided list of Roles.
        """
        roles = validate_roles(roles)
        if isinstance(roles, str):
            roles = [roles]
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(role__in=roles)

    def with_roles_available(self, roles: Union[list, str], entity_slug: str, user_model) -> AccountModelQuerySet:
        """
        Convenience method to pull only available and unlocked AccountModels for a specific EntityModel and for a
        specific list of roles.

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

        if isinstance(roles, str):
            roles = [roles]
        roles = validate_roles(roles)
        qs = self.for_entity_available(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(role__in=roles)

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


class AccountModelAbstract(MP_Node, CreateUpdateMixIn):
    """
    Django Ledger Base Account Model Abstract. This is the main abstract class which the Account Model database will
    inherit, and it contains the fields/columns/attributes which the said ledger table will have. In addition to the
    attributes mentioned below, it also has the fields/columns/attributes mentioned in the ParentChileMixin & the
    CreateUpdateMixIn. Read about these mixin here.

    Below are the fields specific to the accounts model.

    Attributes
    __________

    uuid: UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().

    code: str
        Each account will have its own alphanumeric code.
        For example:
           * Cash Account -> Code 1010.
           * Inventory -> 1200.
        Maximum Length allowed is 10.

    name: str
        This is the user defined name  of the Account. the maximum length for Name of the ledger allowed is 100

    role: str
        Each Account needs to be assigned a certain Role. The exhaustive list of ROLES is defined in io.roles.

    balance_type: str
        Each account will have a default Account type i.e. Either Debit or Credit.
        For example:
            * Assets like Cash, Inventory, Accounts Receivable or Expenses like Rent, Salary will have
              balance_type=DEBIT.
            * Liabilities, Equities and Income like Payables, Loans, Income, Sales, Reserves will have
              balance_type=CREDIT.

    locked: bool
        This determines whether any transactions can be added in the account. Before making any update to the
        account, the account needs to be unlocked. Default value is set to False i.e. Unlocked.

    active: bool
        Determines whether the concerned account is active. Any Account can be used only when it is unlocked and
        Active. Default value is set to True.

    coa: ChartOfAccountsModel
        Each Accounts must be assigned a ChartOfAccountsModel. By default, one CoA will be created for each entity.
        However, the creating of a new AccountModel must have an explicit assignment of a ChartOfAccountModel.

    on_coa: AccountModelManager
        This object has been created for the purpose of the managing the models and in turn handling the database
    """
    BALANCE_TYPE = [
        (CREDIT, _('Credit')),
        (DEBIT, _('Debit'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    code = models.CharField(max_length=10, verbose_name=_('Account Code'))
    name = models.CharField(max_length=100, verbose_name=_('Account Name'))
    role = models.CharField(max_length=30, choices=ACCOUNT_ROLES, verbose_name=_('Account Role'))
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
            ('coa_model', 'code')
        ]
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['balance_type']),
            models.Index(fields=['active']),
            models.Index(fields=['coa_model']),
            models.Index(fields=['role', 'balance_type', 'active']),
        ]

    def __str__(self):
        return '{x1} - {x5}: {x2} ({x3}/{x4})'.format(x1=self.role_bs.upper(),
                                                      x2=self.name,
                                                      x3=self.role.upper(),
                                                      x4=self.balance_type,
                                                      x5=self.code)

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

    def clean(self):
        if not self.code.isalnum():
            raise ValidationError(_('Account code must be alpha numeric, got {%s}') % self.code)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.clean()
        super(AccountModelAbstract, self).save(force_insert=False, force_update=False, using=None, update_fields=None)


class AccountModel(AccountModelAbstract):
    """
    Base Account Model from Account Model Abstract Class
    """
