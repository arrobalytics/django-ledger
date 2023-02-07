"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
    * Pranav P Tulshyan <ptulshyan77@gmail.com>

Chart Of Accounts
_________________

A Chart of Accounts (CoA) is a collection of accounts logically grouped into a distinct set within a
ChartOfAccountModel. The CoA is the backbone of making of any financial statements and it consist of accounts of many
roles, such as cash, accounts receivable, expenses, liabilities, income, etc. For instance, we can have a heading as
"Fixed Assets" in the Balance Sheet, which will consists of Tangible, Intangible Assets. Further, the tangible assets
will consists of multiple accounts like Building, Plant & Equipments, Machinery. So, aggregation of balances of
individual accounts based on the Chart of Accounts and AccountModel roles, helps in preparation of the Financial
Statements.

All EntityModel must have a default CoA to be able to create any type of transaction. Throughout the application,
when no explicit CoA is specified, the default behavior is to use the EntityModel default CoA. **Only ONE Chart of
Accounts can be used when creating Journal Entries**. No commingling between CoAs is allowed in order to preserve the
integrity of the Journal Entry.
"""
from typing import Optional, Union
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.io import (ROOT_COA, ROOT_GROUP_LEVEL_2, ROOT_GROUP_META, ROOT_ASSETS,
                              ROOT_LIABILITIES, ROOT_CAPITAL,
                              ROOT_INCOME, ROOT_COGS, ROOT_EXPENSES)
from django_ledger.models import lazy_loader
from django_ledger.models.accounts import AccountModel, AccountModelQuerySet
from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn
from django_ledger.settings import logger

UserModel = get_user_model()


class ChartOfAccountsModelValidationError(ValidationError):
    pass


class ChartOfAccountQuerySet(models.QuerySet):
    pass


class ChartOfAccountModelManager(models.Manager):
    """
    A custom defined ChartOfAccountModelManager that will act as an interface to handling the initial DB queries
    to the ChartOfAccountModel.
    """

    def for_user(self, user_model) -> ChartOfAccountQuerySet:
        """
        Fetches a QuerySet of ChartOfAccountModel that the UserModel as access to. May include ChartOfAccountModel from
        multiple Entities. The user has access to bills if:
            1. Is listed as Manager of Entity.
            2. Is the Admin of the Entity.

        Parameters
        __________
        user_model
            Logged in and authenticated django UserModel instance.

        Examples
        ________
            >>> request_user = self.request.user
            >>> coa_model_qs = ChartOfAccountModel.objects.for_user(user_model=request_user)

        Returns
        _______
        ChartOfAccountQuerySet
            Returns a ChartOfAccountQuerySet with applied filters.
        """
        qs = self.get_queryset()
        return qs.filter(
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
        )

    def for_entity(self, entity_slug, user_model) -> ChartOfAccountQuerySet:
        """
        Fetches a QuerySet of ChartOfAccountsModel associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        __________

        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.

        user_model
            Logged in and authenticated django UserModel instance.

        Examples
        ________

            >>> request_user = self.request.user
            >>> slug = self.kwargs['entity_slug'] # may come from request kwargs
            >>> coa_model_qs = ChartOfAccountModelManager.objects.for_entity(user_model=request_user, entity_slug=slug)

        Returns
        _______
        ChartOfAccountQuerySet
            Returns a ChartOfAccountQuerySet with applied filters.
        """
        qs = self.get_queryset()
        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return qs.filter(
                Q(entity=entity_slug) &
                (
                        Q(entity__admin=user_model) |
                        Q(entity__managers__in=[user_model])
                )
            )
        return qs.filter(
            Q(entity__slug__iexact=entity_slug) &
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
        )


class ChartOfAccountModelAbstract(SlugNameMixIn, CreateUpdateMixIn):
    """
    Base implementation of Chart of Accounts Model as an Abstract.
    
    2. :func:`CreateUpdateMixIn <django_ledger.models.mixins.SlugMixIn>`
    2. :func:`CreateUpdateMixIn <django_ledger.models.mixins.CreateUpdateMixIn>`
    
    Attributes
    ----------
    uuid : UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().

    entity: EntityModel
        The EntityModel associated with this Chart of Accounts.

    locked: bool
        This determines whether any changes can be done to the Chart of Accounts.
        Before making any update to the ChartOf Account, the account needs to be unlocked.
        Default value is set to False (unlocked).

    description: str
        A user generated description for this Chart of Accounts.
    """

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               verbose_name=_('Entity'),
                               on_delete=models.CASCADE)
    locked = models.BooleanField(default=False, verbose_name=_('Locked'))
    description = models.TextField(verbose_name=_('CoA Description'), null=True, blank=True)
    objects = ChartOfAccountModelManager.from_queryset(queryset_class=ChartOfAccountQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Chart of Account')
        verbose_name_plural = _('Chart of Accounts')
        indexes = [
            models.Index(fields=['entity'])
        ]

    def __str__(self):
        return f'{self.slug}: {self.name}'

    # def is_configured(self, account_model_qs: Optional[AccountModelQuerySet]):
    #     pass

    def get_coa_root_accounts_qs(self) -> AccountModelQuerySet:
        return self.accountmodel_set.all().is_coa_root()

    def get_coa_root(self) -> AccountModel:
        qs = self.get_coa_root_accounts_qs()
        return qs.get(role__exact=ROOT_COA)

    def get_coa_l2_root(self,
                        account_model: AccountModel,
                        root_account_qs: Optional[AccountModelQuerySet] = None,
                        as_queryset: bool = False) -> Union[AccountModelQuerySet, AccountModel]:

        if not account_model.is_coa_root():

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

    def get_coa_account_tree(self):
        root_account = self.get_coa_root()
        return AccountModel.dump_bulk(parent=root_account)

    def configure(self, raise_exception: bool = True):
        root_accounts_qs = self.get_coa_root_accounts_qs()
        existing_root_roles = list(set(acc.role for acc in root_accounts_qs))

        if len(existing_root_roles) > 0:
            raise ChartOfAccountsModelValidationError(message=f'Root Nodes already Exist in CoA {self.uuid}...')

        if ROOT_COA not in existing_root_roles:
            # add coa root...
            role_meta = ROOT_GROUP_META[ROOT_COA]
            account_pk = uuid4()
            logger.info(msg=f'Adding {role_meta} node...')
            coa_root_account_model = AccountModel.add_root(
                instance=AccountModel(
                    uuid=account_pk,
                    code=role_meta['code'],
                    name=role_meta['title'],
                    coa_model=self,
                    role=ROOT_COA,
                    active=False,
                    locked=True,
                    balance_type=role_meta['balance_type']
                ))

            coa_root_account_model = AccountModel.objects.get(uuid__exact=account_pk)

            for root_role in ROOT_GROUP_LEVEL_2:
                if root_role not in existing_root_roles:
                    account_pk = uuid4()
                    role_meta = ROOT_GROUP_META[root_role]
                    logger.info(msg=f'Adding {role_meta} node...')
                    coa_root_account_model.add_child(
                        instance=AccountModel(
                            uuid=account_pk,
                            code=role_meta['code'],
                            name=role_meta['title'],
                            coa_model=self,
                            role=root_role,
                            active=False,
                            locked=True,
                            balance_type=role_meta['balance_type']
                        ))

    def validate_root_coa_qs(self, root_account_qs: AccountModelQuerySet):
        if not isinstance(root_account_qs, AccountModelQuerySet):
            raise ChartOfAccountsModelValidationError(
                message='Must pass an instance of AccountModelQuerySet'
            )
        for acc_model in root_account_qs:
            if not acc_model.coa_model_id == self.uuid:
                raise ChartOfAccountsModelValidationError(
                    message=f'Invalid root queryset for CoA {self.name}'
                )

    def add_account(self, account_model: AccountModel, root_account_qs: Optional[AccountModelQuerySet] = None):
        if not account_model.coa_model_id:
            if not root_account_qs:
                root_account_qs = self.get_coa_root_accounts_qs()
            else:
                self.validate_root_coa_qs(root_account_qs)
            l2_root_node: AccountModel = self.get_coa_l2_root(account_model, root_account_qs=root_account_qs)
            account_model.coa_model = self
            account_model = l2_root_node.add_child(instance=account_model)
        return account_model


class ChartOfAccountModel(ChartOfAccountModelAbstract):
    """
    Base ChartOfAccounts Model
    """
