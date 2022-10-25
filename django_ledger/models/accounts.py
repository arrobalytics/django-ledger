"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
Pranav P Tulshyan <ptulshyan77@gmail.com>
"""
from typing import Union
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ACCOUNT_ROLES, BS_ROLES, GROUP_INVOICE, GROUP_BILL, validate_roles
from django_ledger.models import LazyLoader
from django_ledger.models.mixins import CreateUpdateMixIn, ParentChildMixIn

DEBIT = 'debit'
CREDIT = 'credit'

"""
This is one of the core models as it has the collection of all the accounts in which the transaction will be stored.
Those familiar with the SAP environment, the account is similar to the GL as we know in SAP.
Each entity will be having its list of accounts for cash, rent, salary, loans, payables, sales, income.
We will be looking at the different attributes that the account model will be possessing.  
"""

lazy_loader = LazyLoader()


class AccountModelQuerySet(models.QuerySet):
    """
    This is QuerySet class defined for the Accounts Model.
    """

    def active(self):
        """
        Returns a QuerySet of active AccountModels.
        """
        return self.filter(active=True)

    def with_roles(self, roles: Union[list, str]):
        """
        Returns a QuerySet filtered by user-provided list of Roles. This method is used to make query of accounts
        with a certain role. For instance, the fixed assets like Buildings have all been assigned
        the role of  "asset_ppe_build" role is basically an aggregation of the accounts under a similar category.
        So, to query the list of all accounts under the role "asset_ppe_build", we can use this function.
        Function accepts a single str instance of a role or a list of roles.
        For a list of roles , refer io.roles.py
        """
        if isinstance(roles, str):
            roles = [roles]
        roles = validate_roles(roles)
        return self.filter(role__in=roles)


class AccountModelManager(models.Manager):
    """
    This Model Manager will be used as interface through which the database query operations can be provided to the
    Account Model. It uses the custom defined AccountModelQuerySet and hence overrides the normal get_queryset
    function which return all rows of a model. The "for_entity" method will ensure that a particular entity is able
    to view only their respective accounts. *COA: Each entity will have its individual Chart of Accounts ,
    which will have the mapping for all the accounts of that entity *Discussed in detail in the CoA Model CoA slug,
    basically helps in identifying the complete Chart of Accounts for a Particular Entity.
    """

    def for_entity(self, user_model, entity_slug, coa_slug: str = None):
        """
        The first level filter takes the entity slug or EntityModel and the user model
        In case , even a coa_slug is also passed, the coa_slug will be filtered to show the relevant accounts details

        @param user_model: The default user_model for purpose of access and authorization check.
        @param entity_slug : Entity slug field from URL kwargs or EntityModel.
        @param coa_slug: If None, default CoA will be used.
        @return: QuerySet with the applicable filters.
        """
        qs = self.get_queryset()
        EntityModel = lazy_loader.get_entity_model()
        if isinstance(entity_slug, EntityModel):
            entity_slug = entity_slug.slug
        qs = qs.filter(
            Q(coa__entity__slug__exact=entity_slug) &
            (
                    Q(coa__entity__admin=user_model) |
                    Q(coa__entity__managers__in=[user_model])
            )
        ).order_by('code')
        if coa_slug:
            qs = qs.filter(coa__slug__iexact=coa_slug)
        return qs

    def for_entity_available(self, user_model, entity_slug, coa_slug: str = None):
        """
        Convenience method to pull only available and not locked AccountModels for a specific EntityModel or Entity
        Slug.
        @param user_model: The default user_model for purpose of access and authorization check.
        @param entity_slug : Entity slug field from URL kwargs or EntityModel.
        @param coa_slug: If None, default CoA will be used.
        @return: QuerySet with the applicable filters.
        """
        qs = self.for_entity(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(
            active=True,
            locked=False
        )

    def with_roles(self, roles: Union[list, str], entity_slug: str, user_model):
        """
        @param roles : The roles can be in form of a single string or even a list.
        @param entity_slug : Expected data type is string.
        @param user_model: The default user_model for purpose of access and authorization check.
        @return: QuerySet with the applicable filters
        """
        if isinstance(roles, str):
            roles = [roles]
        qs = self.for_entity(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(role__in=roles)

    def with_roles_available(self, roles: Union[list, str], entity_slug: str, user_model):
        """
        Returns the accounts which are available (i.e. not locked and are marked as active) for a single or a list of
        account roles.
        @param roles: The roles can be in form of a single string or even a list.
        @param entity_slug : Expected data type is string.
        @param user_model: The default user_model for purpose of access and authorization check.
        @return: QuerySet with the applicable filters
        """

        if isinstance(roles, str):
            roles = [roles]
        roles = validate_roles(roles)
        qs = self.for_entity_available(entity_slug=entity_slug, user_model=user_model)
        return qs.filter(role__in=roles)

    def for_invoice(self, user_model, entity_slug: str, coa_slug: str = None):
        """
        Applies the filter for selection for accounts which are assigned the roles as marked under "GROUP_INVOICE".

        @param entity_slug : Expected data type is string.
        @param coa_slug: Expected data type is string. If None, default CoA will be used.
        @param user_model: The default user_model for purpose of access and authorization check.
        @return: QuerySet with the applicable filters
        """
        qs = self.for_entity_available(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(role__in=GROUP_INVOICE)

    def for_bill(self, user_model, entity_slug, coa_slug: str = None):
        """
        Applies the filter for selection of the account which are assigned the roles as marked under "GROUP_BILL"
        @param entity_slug : Expected data type is string.
        @param coa_slug: Expected data type is string. If None, default CoA will be used.
        @param user_model: The default user_model for purpose of access and authorization check.
        @return: QuerySet with the applicable filters
        """

        qs = self.for_entity_available(
            user_model=user_model,
            entity_slug=entity_slug,
            coa_slug=coa_slug)
        return qs.filter(role__in=GROUP_BILL)


class AccountModelAbstract(ParentChildMixIn, CreateUpdateMixIn):
    """
    Django Ledger Base Account Model Abstract. This is the main abstract class which the Account Model database will
    inherit, and it contains the fields/columns/attributes which the said ledger table will have. In addition to the
    attributes mentioned below, it also has the fields/columns/attributes mentioned in the ParentChileMixin & the
    CreateUpdateMixIn. Read about these mixin here.

    Below are the fields specific to the accounts model.

    uuid : this is a unique primary key generated for the table. the default value of this field is uuid4().
    code: Each account will have its own code for e.g. Cash Account -> Code 1010 , Inventory -> 1200. Maximum Length
    allowed is 10.
    name: This is the user defined name  of the Account. the maximum length for Name of the ledger allowed is 100
    role : Each Account needs to be assigned a certain Role. The exhaustive list of ROLES is defined in io.roles.
    balance_type: Each account will have a default Account type i.e. Either Debit or Credit. For example: Assets like
    Cash, Inventory, Accounts_receivable or Expenses like Rent, Salary will have BALANCE_TYPE="Debit" Liabilities,
    Equities and Income like Payables, Loans, Income, Sales, Reserves will have BALANCE_TYPE="Credit"
    locked:This determines whether any changes can be done in the account or not. Before making any update to the
    account, the account needs to be unlocked Default value is set to False i.e. Unlocked
    active: Determines whether the concerned account is active. Any Account can be used only when it is unlocked and
    Active Default value is set to False i.e Unlocked
    coa: Each Accounts must be assigned a set of Chart_of_Accounts. By default ,one CoA will be created for each entity.
    All account created within that particular entity will all be mapped to that coa.
    on_coa: This object has been created for the purpose of the managing the models and in turn handling the database

    Some Meta Information: (Additional data points regarding this model that may alter its behavior)

    @abstract: This is a abstract class and will be used through inheritance. Separate implementation can be done for
    this abstract class. [It may also be noted that models are not created for the abstract models, but only for the
    models which implements the abstract model class]
    @verbose_name: A human-readable name for this Model (Also translatable to other languages with django translation
    gettext_lazy).
    @unique_together: the concatenation of coa & account code would remain unique throughout the model i.e. database
    @indexes : Index created on different attributes for better db & search queries
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
    coa = models.ForeignKey('django_ledger.ChartOfAccountModel',
                            on_delete=models.CASCADE,
                            editable=False,
                            verbose_name=_('Chart of Accounts'),
                            related_name='accounts')
    on_coa = AccountModelManager.from_queryset(queryset_class=AccountModelQuerySet)()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        unique_together = [
            ('coa', 'code')
        ]
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['balance_type']),
            models.Index(fields=['active']),
            models.Index(fields=['coa']),
            models.Index(fields=['role', 'balance_type', 'active']),
        ]

    def __str__(self):
        return '{x1} - {x5}: {x2} ({x3}/{x4})'.format(x1=self.role_bs.upper(),
                                                      x2=self.name,
                                                      # pylint: disable=no-member
                                                      x3=self.role.upper(),
                                                      x4=self.balance_type,
                                                      x5=self.code)

    @property
    def role_bs(self):
        return BS_ROLES.get(self.role)

    def is_debit(self):
        return self.balance_type == DEBIT

    def is_credit(self):
        return self.balance_type == CREDIT

    def clean(self):
        # pylint: disable=unsupported-membership-test
        if ' ' in self.code:
            raise ValidationError(_('Account code must not contain spaces'))


class AccountModel(AccountModelAbstract):
    """
    Base Account Model from Account Model Abstract Class
    """
