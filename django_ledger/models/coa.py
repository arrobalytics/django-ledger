"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
    * Pranav P Tulshyan <ptulshyan77@gmail.com>

Chart Of Accounts
_________________

A Chart of Accounts (CoA) is a crucial collection of logically grouped accounts within a ChartOfAccountModel,
forming the backbone of financial statements. The CoA includes various account roles such as cash, accounts receivable,
expenses, liabilities, and income. For example, the Balance Sheet may have a Fixed Assets heading consisting of
Tangible and Intangible Assets with multiple accounts like Building, Plant &amp; Equipments, and Machinery under
tangible assets. Aggregation of individual account balances based on the Chart of Accounts and AccountModel roles is
essential for preparing Financial Statements.

All EntityModel must have a default CoA to create any type of transaction. When no explicit CoA is specified, the
default behavior is to use the EntityModel default CoA. Only ONE Chart of Accounts can be used when creating
Journal Entries. No commingling between CoAs is allowed to preserve the integrity of the Journal Entry.
"""
from random import choices
from string import ascii_lowercase, digits
from typing import Optional, Union, Dict
from uuid import uuid4

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.io import (ROOT_COA, ROOT_GROUP_LEVEL_2, ROOT_GROUP_META, ROOT_ASSETS,
                              ROOT_LIABILITIES, ROOT_CAPITAL,
                              ROOT_INCOME, ROOT_COGS, ROOT_EXPENSES)
from django_ledger.models import lazy_loader
from django_ledger.models.accounts import AccountModel, AccountModelQuerySet
from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn

UserModel = get_user_model()

SLUG_SUFFIX = ascii_lowercase + digits

app_config = apps.get_app_config('django_ledger')


class ChartOfAccountsModelValidationError(ValidationError):
    pass


class ChartOfAccountModelQuerySet(models.QuerySet):

    def active(self):
        """
        QuerySet method to retrieve active items.
        """
        return self.filter(active=True)


class ChartOfAccountModelManager(models.Manager):
    """
    A custom defined ChartOfAccountModelManager that will act as an interface to handling the initial DB queries
    to the ChartOfAccountModel.
    """

    def for_user(self, user_model) -> ChartOfAccountModelQuerySet:
        """
        Fetches a QuerySet of ChartOfAccountModel that the UserModel as access to. May include ChartOfAccountModel from
        multiple Entities. The user has access to bills if:
        1. Is listed as Manager of Entity.
        2. Is the Admin of the Entity.

        Parameters
        ----------
        user_model
            Logged in and authenticated django UserModel instance.

        Returns
        -------
        ChartOfAccountQuerySet
            Returns a ChartOfAccountQuerySet with applied filters.
        """
        qs = self.get_queryset()
        return qs.filter(
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
        ).select_related('entity')

    def for_entity(self, entity_slug, user_model) -> ChartOfAccountModelQuerySet:
        """
        Fetches a QuerySet of ChartOfAccountsModel associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        __________

        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.

        user_model
            Logged in and authenticated django UserModel instance.

        Returns
        -------
        ChartOfAccountQuerySet
            Returns a ChartOfAccountQuerySet with applied filters.
        """
        qs = self.for_user(user_model)
        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return qs.filter(entity=entity_slug).select_related('entity')
        return qs.filter(entity__slug__iexact=entity_slug).select_related('entity')


class ChartOfAccountModelAbstract(SlugNameMixIn, CreateUpdateMixIn):
    """
    Abstract base class for the Chart of Account model.

    Attributes
    ----------
    uuid : UUIDField
        UUID field for the chart of account model (primary key).
    entity : ForeignKey
        ForeignKey to the EntityModel.
    active : BooleanField
        BooleanField indicating whether the chart of account is active or not.
    description : TextField
        TextField storing the description of the chart of account.
    objects : ChartOfAccountModelManager
        Manager for the ChartOfAccountModel.
    """

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               verbose_name=_('Entity'),
                               on_delete=models.CASCADE)
    active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    description = models.TextField(verbose_name=_('CoA Description'), null=True, blank=True)
    objects = ChartOfAccountModelManager.from_queryset(queryset_class=ChartOfAccountModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Chart of Account')
        verbose_name_plural = _('Chart of Accounts')
        indexes = [
            models.Index(fields=['entity'])
        ]

    def __str__(self):
        if self.name is not None:
            return f'{self.name} ({self.slug})'
        return self.slug

    def get_coa_root_accounts_qs(self) -> AccountModelQuerySet:
        """
        Retrieves the root accounts in the chart of accounts.

        Returns:
            AccountModelQuerySet: A queryset containing the root accounts in the chart of accounts.
        """
        return self.accountmodel_set.all().is_coa_root()

    def get_coa_root_node(self) -> AccountModel:
        """
        Retrieves the root node of the chart of accounts.

        Returns:
            AccountModel: The root node of the chart of accounts.

        """
        qs = self.get_coa_root_accounts_qs()
        return qs.get(role__exact=ROOT_COA)

    def get_account_root_node(self,
                              account_model: AccountModel,
                              root_account_qs: Optional[AccountModelQuerySet] = None,
                              as_queryset: bool = False) -> AccountModel:
        """
        Fetches the root node of the ChartOfAccountModel instance. The root node is the highest level of the CoA
        hierarchy. It can be used to traverse the hierarchy of the CoA structure downstream.


        Parameters
        ----------
        account_model : AccountModel
            The account model for which to find the root node.
        root_account_qs : Optional[AccountModelQuerySet], optional
            The queryset of root accounts. If not provided, it will be retrieved using `get_coa_root_accounts_qs` method.
        as_queryset : bool, optional
            If True, return the root account queryset instead of a single root account. Default is False.

        Returns
        -------
        Union[AccountModelQuerySet, AccountModel]
            If `as_queryset` is True, returns the root account queryset. Otherwise, returns a single root account.

        Raises
        ------
        ChartOfAccountsModelValidationError
            If the account model is not part of the chart of accounts.
        """

        if account_model.coa_model_id != self.uuid:
            raise ChartOfAccountsModelValidationError(
                message=_(f'The account model {account_model} is not part of the chart of accounts {self.name}.'),
            )

        if not account_model.is_root_account():

            if not root_account_qs:
                root_account_qs = self.get_coa_root_accounts_qs()

            if account_model.is_asset():
                qs = root_account_qs.filter(code__exact=ROOT_GROUP_META[ROOT_ASSETS]['code'])
            elif account_model.is_liability():
                qs = root_account_qs.filter(code__exact=ROOT_GROUP_META[ROOT_LIABILITIES]['code'])
            elif account_model.is_capital():
                qs = root_account_qs.filter(code__exact=ROOT_GROUP_META[ROOT_CAPITAL]['code'])
            elif account_model.is_income():
                qs = root_account_qs.filter(code__exact=ROOT_GROUP_META[ROOT_INCOME]['code'])
            elif account_model.is_cogs():
                qs = root_account_qs.filter(code__exact=ROOT_GROUP_META[ROOT_COGS]['code'])
            elif account_model.is_expense():
                qs = root_account_qs.filter(code__exact=ROOT_GROUP_META[ROOT_EXPENSES]['code'])
            else:
                raise ChartOfAccountsModelValidationError(message=f'Unable to locate Balance Sheet'
                                                                  ' root node for account code: '
                                                                  f'{account_model.code} {account_model.name}')
            if as_queryset:
                return qs
            return qs.get()

    def get_non_root_coa_accounts_qs(self) -> AccountModelQuerySet:
        """
        Returns a query set of non-root accounts in the chart of accounts.

        Returns
        -------
        AccountModelQuerySet
            A query set of non-root accounts in the chart of accounts.
        """
        return self.accountmodel_set.all().not_coa_root()

    def get_coa_accounts(self, active_only: bool = True) -> AccountModelQuerySet:
        """
        Returns the AccountModelQuerySet associated with the ChartOfAccounts model instance.

        Parameters
        ----------
        active_only : bool, optional
            Flag to indicate whether to retrieve only active accounts or all accounts.
            Default is True.

        Returns
        -------
        AccountModelQuerySet
            A queryset containing accounts from the chart of accounts.

        """
        qs = self.get_non_root_coa_accounts_qs()
        if active_only:
            return qs.active()
        return qs

    def get_coa_account_tree(self) -> Dict:
        """
        Performs a bulk dump of the ChartOfAccounts model instance accounts to a dictionary.
        The method invokes the`dump_bulk` method on the ChartOfAccount model instance root node.
        See Django Tree Beard documentation for more information.

        Returns
        -------
        Dict
            A dictionary containing all accounts from the chart of accounts in a nested structure.
        """
        root_account = self.get_coa_root_node()
        return AccountModel.dump_bulk(parent=root_account)

    def generate_slug(self, raise_exception: bool = False) -> str:
        """
        Generates and assigns a slug based on the ChartOfAccounts model instance EntityModel information.


        Parameters
        ----------
        raise_exception : bool, optional
                If set to True, it will raise a ChartOfAccountsModelValidationError if the `self.slug` is already set.

        Returns
        -------
        str
                The generated slug for the Chart of Accounts.

        Raises
        ------
        ChartOfAccountsModelValidationError
                If `raise_exception` is set to True and `self.slug` is already set.

        """
        if self.slug:
            if raise_exception:
                raise ChartOfAccountsModelValidationError(
                    message=_(f'CoA {self.uuid} already has a slug')
                )
            return
        self.slug = f'coa-{self.entity.slug[-5:]}-' + ''.join(choices(SLUG_SUFFIX, k=15))

    def configure(self, raise_exception: bool = True):
        """
        A method that properly configures the ChartOfAccounts model and creates the appropriate hierarchy boilerplate
        to support the insertion of new accounts into the chart of account model tree.
        This method must be called every time the ChartOfAccounts model is created.

        Parameters
        ----------
        raise_exception : bool, optional
            Whether to raise an exception if root nodes already exist in the Chart of Accounts (default is True).
            This indicates that the ChartOfAccountModel instance is already configured.
        """
        self.generate_slug()

        root_accounts_qs = self.get_coa_root_accounts_qs()
        existing_root_roles = list(set(acc.role for acc in root_accounts_qs))

        if len(existing_root_roles) > 0:
            if raise_exception:
                raise ChartOfAccountsModelValidationError(message=f'Root Nodes already Exist in CoA {self.uuid}...')
            return

        if ROOT_COA not in existing_root_roles:
            # add coa root...
            role_meta = ROOT_GROUP_META[ROOT_COA]
            account_pk = uuid4()
            root_account = AccountModel(
                uuid=account_pk,
                code=role_meta['code'],
                name=role_meta['title'],
                coa_model=self,
                role=ROOT_COA,
                role_default=True,
                active=False,
                locked=True,
                balance_type=role_meta['balance_type']
            )
            AccountModel.add_root(instance=root_account)

            # must retrieve root model after added pero django-treebeard documentation...
            coa_root_account_model = AccountModel.objects.get(uuid__exact=account_pk)

            for root_role in ROOT_GROUP_LEVEL_2:
                if root_role not in existing_root_roles:
                    account_pk = uuid4()
                    role_meta = ROOT_GROUP_META[root_role]
                    coa_root_account_model.add_child(
                        instance=AccountModel(
                            uuid=account_pk,
                            code=role_meta['code'],
                            name=role_meta['title'],
                            coa_model=self,
                            role=root_role,
                            role_default=True,
                            active=False,
                            locked=True,
                            balance_type=role_meta['balance_type']
                        ))

    def is_default(self) -> bool:
        """
        Check if the ChartOfAccountModel instance is set as the default for the EntityModel.

        Returns
        -------
        bool
            True if the ChartOfAccountModel instance is set as the default for the EntityModel. Else, False.
        """
        if not self.entity_id:
            return False
        if not self.entity.default_coa_id:
            return False
        return self.entity.default_coa_id == self.uuid

    def is_active(self) -> bool:
        """
        Check if the ChartOfAccountModel instance is active.

        Returns:
            bool: True if the ChartOfAccountModel instance is active, False otherwise.
        """
        return self.active is True

    def validate_account_model_qs(self, account_model_qs: AccountModelQuerySet):
        """
        Validates the given AccountModelQuerySet for the ChartOfAccountsModel.

        Parameters
        ----------
        account_model_qs : AccountModelQuerySet
            The AccountModelQuerySet to validate.

        Raises
        ------
        ChartOfAccountsModelValidationError
            If the account_model_qs is not an instance of AccountModelQuerySet or if it contains an account model with a different coa_model_id than the current CoA model.

        """
        if not isinstance(account_model_qs, AccountModelQuerySet):
            raise ChartOfAccountsModelValidationError(
                message='Must pass an instance of AccountModelQuerySet'
            )
        for acc_model in account_model_qs:
            if not acc_model.coa_model_id == self.uuid:
                raise ChartOfAccountsModelValidationError(
                    message=f'Invalid root queryset for CoA {self.name}'
                )

    def insert_account(self,
                       account_model: AccountModel,
                       root_account_qs: Optional[AccountModelQuerySet] = None):
        """
        This method inserts the given account model into the chart of accounts (COA) instance.
        It first verifies if the account model's COA model ID matches the COA's UUID. If not, it
        raises a `ChartOfAccountsModelValidationError`. If the `root_account_qs` is not provided, it retrieves the
        root account query set using the `get_coa_root_accounts_qs` method. Providing a pre-fetched `root_account_qs`
        avoids unnecessary retrieval of the root account query set every an account model is inserted into the CoA.

        Next, it validates the provided `root_account_qs` if it is not None. Then, it obtains the root node for the
        account model using the `get_account_root_node` method and assigns it to `account_root_node`.

        Finally, it adds the account model as a child to the `account_root_node` and retrieves the updated COA accounts
        query set using the `get_non_root_coa_accounts_qs` method. It returns the inserted account model found in the
        COA accounts query set.

        Parameters
        ----------
        account_model : AccountModel
            The account model to be inserted into the chart of accounts.
        root_account_qs : Optional[AccountModelQuerySet], default=None
            The root account query set. If not provided, it will be obtained using the `get_coa_root_accounts_qs`
            method.

        Returns
        -------
        AccountModel
            The inserted account model.

        Raises
        ------
        ChartOfAccountsModelValidationError
            If the provided account model has an invalid COA model ID for the current COA.
        """

        if account_model.coa_model_id:
            if account_model.coa_model_id != self.uuid:
                raise ChartOfAccountsModelValidationError(
                    message=f'Invalid Account Model {account_model} for CoA {self}'
                )
        else:
            account_model.coa_model = self

        if not root_account_qs:
            root_account_qs = self.get_coa_root_accounts_qs()
        else:
            self.validate_account_model_qs(root_account_qs)

        account_root_node: AccountModel = self.get_account_root_node(
            account_model=account_model,
            root_account_qs=root_account_qs
        )

        account_root_node.add_child(instance=account_model)
        coa_accounts_qs = self.get_non_root_coa_accounts_qs()
        return coa_accounts_qs.get(uuid__exact=account_model.uuid)

    def create_account(self,
                       code: str,
                       role: str,
                       name: str,
                       balance_type: str,
                       active: bool,
                       root_account_qs: Optional[AccountModelQuerySet] = None):
        """
        Proper method for inserting a new Account Model into a CoA.
        Use this in liu of the direct instantiation of the AccountModel of using the django related manager.

        Parameters
        ----------
        code : str
            The code of the account to be created.
        role : str
            The role of the account. This can be a user-defined value.
        name : str
            The name of the account.
        balance_type : str
            The balance type of the account. This can be a user-defined value.
        active : bool
            Specifies whether the account is active or not.
        root_account_qs : Optional[AccountModelQuerySet], optional
            The query set of root accounts to which the created account should be linked. Defaults to None.

        Returns
        -------
        AccountModel
            The created account model instance.
        """
        account_model = AccountModel(
            code=code,
            name=name,
            role=role,
            active=active,
            balance_type=balance_type,
            coa_model=self
        )
        account_model.clean()

        account_model = self.insert_account(
            account_model=account_model,
            root_account_qs=root_account_qs
        )
        return account_model

    # ACTIONS -----
    # todo: use these methods once multi CoA features are enabled...
    def lock_all_accounts(self) -> AccountModelQuerySet:
        account_qs = self.get_coa_accounts()
        account_qs.update(locked=True)
        return account_qs

    def unlock_all_accounts(self) -> AccountModelQuerySet:
        account_qs = self.get_non_root_coa_accounts_qs()
        account_qs.update(locked=False)
        return account_qs

    def mark_as_default(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        """
        Marks the current Chart of Accounts instances as default for the EntityModel.

        Parameters
        ----------
        commit: bool
            Commit the action into the Database. Default is False.
        raise_exception: bool
            Raises exception if Chart of Account model instance is already marked as default.
        """
        if self.is_default():
            if raise_exception:
                raise ChartOfAccountsModelValidationError(
                    message=_(f'The Chart of Accounts {self.slug} is already default')
                )
            return
        self.entity.default_coa_id = self.uuid
        self.clean()
        if commit:
            self.entity.save(
                update_fields=[
                    'default_coa_id',
                    'updated'
                ]
            )

    def mark_as_default_url(self) -> str:
        """
        Returns the URL to mark the current Chart of Accounts instances as Default for the EntityModel.

        Returns
        -------
        str
            The URL as a String.
        """
        return reverse(
            viewname='django_ledger:coa-action-mark-as-default',
            kwargs={
                'entity_slug': self.entity.slug,
                'coa_slug': self.slug
            }
        )

    def can_activate(self) -> bool:
        """
        Check if the ChartOffAccountModel instance can be activated.

        Returns
        -------
            True if the object can be activated, False otherwise.
        """
        return self.active is False

    def can_deactivate(self) -> bool:
        """
        Check if the ChartOffAccountModel instance can be deactivated.

        Returns
        -------
            True if the object can be deactivated, False otherwise.
        """
        return all([
            self.is_active(),
            not self.is_default()
        ])

    def mark_as_active(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        """
        Marks the current Chart of Accounts as Active.

        Parameters
        ----------
        commit: bool
            Commit the action into the Database. Default is False.
        raise_exception: bool
            Raises exception if Chart of Account model instance is already active. Default is False.
        """
        if self.is_active():
            if raise_exception:
                raise ChartOfAccountsModelValidationError(
                    message=_('The Chart of Accounts is currently active.')
                )
            return

        self.active = True
        self.clean()
        if commit:
            self.save(
                update_fields=[
                    'active',
                    'updated'
                ])

    def mark_as_active_url(self) -> str:
        """
        Returns the URL to mark the current Chart of Accounts instances as active.

        Returns
        -------
        str
            The URL as a String.
        """
        return reverse(
            viewname='django_ledger:coa-action-mark-as-active',
            kwargs={
                'entity_slug': self.entity.slug,
                'coa_slug': self.slug
            }
        )

    def mark_as_inactive(self, commit: bool = False, raise_exception: bool = False, **kwargs):
        """
        Marks the current Chart of Accounts as Active.

        Parameters
        ----------
        commit: bool
            Commit the action into the Database. Default is False.
        raise_exception: bool
            Raises exception if Chart of Account model instance is already active. Default is False.
        """
        if not self.is_active():
            if raise_exception:
                raise ChartOfAccountsModelValidationError(
                    message=_('The Chart of Accounts is currently not active.')
                )
            return

        self.active = False
        self.clean()
        if commit:
            self.save(
                update_fields=[
                    'active',
                    'updated'
                ])

    def mark_as_inactive_url(self) -> str:
        """
        Returns the URL to mark the current Chart of Accounts instances as inactive.

        Returns
        -------
        str
            The URL as a String.
        """
        return reverse(
            viewname='django_ledger:coa-action-mark-as-inactive',
            kwargs={
                'entity_slug': self.entity.slug,
                'coa_slug': self.slug
            }
        )

    def get_coa_list_url(self):
        return reverse(
            viewname='django_ledger:coa-list',
            kwargs={
                'entity_slug': self.entity.slug
            }
        )

    def get_absolute_url(self) -> str:
        return reverse(
            viewname='django_ledger:coa-detail',
            kwargs={
                'coa_slug': self.slug,
                'entity_slug': self.entity.slug
            }
        )

    def get_account_list_url(self):
        return reverse(
            viewname='django_ledger:account-list-coa',
            kwargs={
                'entity_slug': self.entity.slug,
                'coa_slug': self.slug
            }
        )

    def get_create_coa_account_url(self):
        return reverse(
            viewname='django_ledger:account-create-coa',
            kwargs={
                'coa_slug': self.slug,
                'entity_slug': self.entity.slug
            }
        )

    def clean(self):
        self.generate_slug()
        if self.is_default() and not self.active:
            raise ChartOfAccountsModelValidationError(
                _('Default Chart of Accounts cannot be deactivated.')
            )


class ChartOfAccountModel(ChartOfAccountModelAbstract):
    """
    Base ChartOfAccounts Model
    """
