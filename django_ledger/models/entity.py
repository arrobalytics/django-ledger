"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
    * Pranav P Tulshyan ptulshyan77@gmail.com<>

The EntityModel represents the Company, Corporation, Legal Entity, Enterprise or Person that engage and operate as a
business. EntityModels can be created as part of a parent/child model structure to accommodate complex corporate
structures where certain entities may be owned by other entities and may also generate consolidated financial statements.
Another use case of parent/child model structures is the coordination and authorization of inter-company transactions
across multiple related entities. The EntityModel encapsulates all LedgerModel, JournalEntryModel and TransactionModel which is the core structure of
Django Ledger in order to track and produce all financials.

The EntityModel must be assigned an Administrator at creation, and may have optional Managers that will have the ability
to operate on such EntityModel.

EntityModels may also have different financial reporting periods, (also known as fiscal year), which start month is
specified at the time of creation. All key functionality around the Fiscal Year is encapsulated in the
EntityReportMixIn.

"""
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from random import choices
from string import ascii_lowercase, digits
from typing import Tuple, Union, Optional, List, Dict
from uuid import uuid4, UUID

from django.contrib.auth import get_user_model
from django.core import serializers
from django.core.cache import caches
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, QuerySet
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.text import slugify
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from treebeard.mp_tree import MP_Node, MP_NodeManager, MP_NodeQuerySet

from django_ledger.io import roles as roles_module, validate_roles, IODigestContextManager
from django_ledger.io.io_mixin import IOMixIn
from django_ledger.models.accounts import AccountModel, AccountModelQuerySet, DEBIT, CREDIT
from django_ledger.models.bank_account import BankAccountModelQuerySet, BankAccountModel
from django_ledger.models.coa import ChartOfAccountModel, ChartOfAccountModelQuerySet
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS_ROOT_MAP
from django_ledger.models.customer import CustomerModelQueryset, CustomerModel
from django_ledger.models.items import (ItemModelQuerySet, ItemTransactionModelQuerySet,
                                        UnitOfMeasureModel, UnitOfMeasureModelQuerySet, ItemModel)
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn, ContactInfoMixIn, LoggingMixIn
from django_ledger.models.unit import EntityUnitModel
from django_ledger.models.utils import lazy_loader
from django_ledger.models.vendor import VendorModelQuerySet, VendorModel
from django_ledger.settings import DJANGO_LEDGER_DEFAULT_CLOSING_ENTRY_CACHE_TIMEOUT

UserModel = get_user_model()

ENTITY_RANDOM_SLUG_SUFFIX = ascii_lowercase + digits


class EntityModelValidationError(ValidationError):
    pass


class EntityModelQuerySet(MP_NodeQuerySet):
    """
    A custom defined EntityModel QuerySet.
    Inherits from the Materialized Path Node QuerySet Class from Django Treebeard.
    """

    def hidden(self):
        """
        A QuerySet of all hidden EntityModel.

        Returns
        -------
        EntityModelQuerySet
            A filtered QuerySet of hidden EntityModels only.
        """
        return self.filter(hidden=True)

    def visible(self):
        """
        A Queryset of all visible EntityModel.

        Returns
        -------
        EntityModelQuerySet
            A filtered QuerySet of visible EntityModels only.
        """
        return self.filter(hidden=False)


class EntityModelManager(MP_NodeManager):
    """
    A custom defined EntityModel Manager. This ModelManager uses the custom defined EntityModelQuerySet as default.
    Inherits from the Materialized Path Node Manager to include the necessary methods to manage tree-like models.
    This Model Manager keeps track and maintains a root/parent/child relationship between Entities for the purposes of
    producing consolidated financial statements.

    Examples
    ________
    >>> user = request.user
    >>> entity_model_qs = EntityModel.objects.for_user(user_model=user)

    """

    def get_queryset(self):
        """Sets the custom queryset as the default."""
        return EntityModelQuerySet(self.model).order_by('path').select_related('admin', 'default_coa')

    def for_user(self, user_model):
        """
        This QuerySet guarantees that Users do not access or operate on EntityModels that don't have access to.
        This is the recommended initial QuerySet.

        Parameters
        ----------
        user_model
            The Django User Model making the request.

        Returns
        -------
        EntityModelQuerySet
            A filtered QuerySet of EntityModels that the user has access. The user has access to an Entity if:
                1. Is the Administrator.
                2. Is a manager.
        """
        qs = self.get_queryset()
        return qs.filter(
            Q(admin=user_model) |
            Q(managers__in=[user_model])
        )


class FiscalPeriodMixIn:
    """
    This class encapsulates the functionality needed to determine the start and end of all financial periods of an
    EntityModel. At the moment of creation, an EntityModel must be assigned a calendar month which is going to
    determine the start of the Fiscal Year.
    """
    VALID_QUARTERS = list(range(1, 5))
    VALID_MONTHS = list(range(1, 13))

    def get_fy_start_month(self) -> int:
        """
        The fiscal year start month represents the month (as an integer) when the assigned fiscal year of the
        EntityModel starts.

        Returns
        -------
        int
            An integer representing the month that the fiscal year starts.

        Examples
        ________
            * 1 -> January.
            * 4 -> April.
            * 9 -> September.
        """

        try:
            fy: int = getattr(self, 'fy_start_month')
        except AttributeError:
            # current object is not an entity, get current entity and fetch its fy_start_month value

            # if current object is a detail view with an object...
            obj = getattr(self, 'object')
            if isinstance(obj, EntityModel):
                entity = obj
            elif isinstance(obj, LedgerModel):
                entity = obj.entity
            elif isinstance(obj, EntityUnitModel):
                entity = obj.entity
            elif isinstance(obj, AccountModel):
                entity = obj.coa_model.entity

            fy: int = getattr(entity, 'fy_start_month')

        return fy

    def validate_quarter(self, quarter: int):
        """
        Validates the quarter as a valid parameter for other functions.
        Makes sure that only integers 1,2,3, or 4 are used to refer to a particular Quarter.
        Prevents injection of invalid values from views into the IOMixIn.

        Parameters
        ----------
        quarter: int
            The quarter number to validate.

        Raises
        ------
        ValidationError
            If quarter is not valid.
        """
        if quarter not in self.VALID_QUARTERS:
            raise ValidationError(f'Specified quarter is not valid: {quarter}')

    def validate_month(self, month: int):
        """
        Validates the month as a valid parameter for other functions.
        Makes sure that only integers between 1 and 12 are used to refer to a particular month.
        Prevents injection of invalid values from views into the IOMixIn.

        Parameters
        ----------
        month: int
            The month number to validate.

        Raises
        ------

        ValidationError
            If month is not valid.
        """
        if month not in self.VALID_MONTHS:
            raise ValidationError(f'Specified month is not valid: {month}')

    def get_fy_start(self, year: int, fy_start_month: Optional[int] = None) -> date:
        """
        The fiscal year start date of the EntityModel, according to its settings.

        Parameters
        ----------
        year: int
            The fiscal year associated with the requested start date.

        fy_start_month: int
            Optional fiscal year month start. If passed, it will override the EntityModel setting.

        Returns
        -------
        date
            The date when the requested EntityModel fiscal year starts.
        """
        if fy_start_month:
            self.validate_month(fy_start_month)
        fy_start_month = self.get_fy_start_month() if not fy_start_month else fy_start_month
        return date(year, fy_start_month, 1)

    def get_fy_end(self, year: int, fy_start_month: int = None) -> date:
        """
        The fiscal year ending date of the EntityModel, according to its settings.

        Parameters
        ----------
        year: int
            The fiscal year associated with the requested end date.

        fy_start_month: int
            Optional fiscal year month start. If passed, it will override the EntityModel setting.

        Returns
        -------
        date
            The date when the requested EntityModel fiscal year ends.
        """
        if fy_start_month:
            self.validate_month(fy_start_month)
        fy_start_month = self.get_fy_start_month() if not fy_start_month else fy_start_month
        ye = year if fy_start_month == 1 else year + 1
        me = 12 if fy_start_month == 1 else fy_start_month - 1
        return date(ye, me, monthrange(ye, me)[1])

    def get_quarter_start(self, year: int, quarter: int, fy_start_month: int = None) -> date:
        """
        The fiscal year quarter starting date of the EntityModel, according to its settings.

        Parameters
        ----------
        year: int
            The fiscal year associated with the requested start date.

        quarter: int
            The quarter number associated with the requested start date.

        fy_start_month: int
            Optional fiscal year month start. If passed, it will override the EntityModel setting.

        Returns
        -------
        date
            The date when the requested EntityModel quarter starts.
        """
        if fy_start_month:
            self.validate_month(fy_start_month)
        fy_start_month = self.get_fy_start_month() if not fy_start_month else fy_start_month
        self.validate_quarter(quarter)
        quarter_month_start = (quarter - 1) * 3 + fy_start_month
        year_start = year
        if quarter_month_start > 12:
            quarter_month_start -= 12
            year_start = year + 1
        return date(year_start, quarter_month_start, 1)

    def get_quarter_end(self, year: int, quarter: int, fy_start_month: int = None) -> date:
        """
        The fiscal year quarter ending date of the EntityModel, according to its settings.

        Parameters
        ----------
        year: int
            The fiscal year associated with the requested end date.

        quarter: int
            The quarter number associated with the requested end date.

        fy_start_month: int
            Optional fiscal year month start. If passed, it will override the EntityModel setting.

        Returns
        -------
        date
            The date when the requested EntityModel quarter ends.
        """
        if fy_start_month:
            self.validate_month(fy_start_month)
        fy_start_month = self.get_fy_start_month() if not fy_start_month else fy_start_month
        self.validate_quarter(quarter)
        quarter_month_end = quarter * 3 + fy_start_month - 1
        year_end = year
        if quarter_month_end > 12:
            quarter_month_end -= 12
            year_end += 1
        return date(year_end, quarter_month_end, monthrange(year_end, quarter_month_end)[1])

    def get_fiscal_year_dates(self, year: int, fy_start_month: int = None) -> Tuple[date, date]:
        """
        Convenience method to get in one shot both, fiscal year start and end dates.

        Parameters
        ----------
        year: int
            The fiscal year associated with the requested start and end date.

        fy_start_month: int
            Optional fiscal year month start. If passed, it will override the EntityModel setting.

        Returns
        -------
        tuple
            Both, the date when the requested EntityModel fiscal year start and end date as a tuple.
            The start date will be first.

        """
        if fy_start_month:
            self.validate_month(fy_start_month)
        sd = self.get_fy_start(year, fy_start_month)
        ed = self.get_fy_end(year, fy_start_month)
        return sd, ed

    def get_fiscal_quarter_dates(self, year: int, quarter: int, fy_start_month: int = None) -> Tuple[date, date]:
        """
        Convenience method to get in one shot both, fiscal year quarter start and end dates.

        Parameters
        ----------
        year: int
            The fiscal year associated with the requested start and end date.

        quarter: int
            The quarter number associated with the requested start and end date.

        fy_start_month: int
            Optional fiscal year month start. If passed, it will override the EntityModel setting.

        Returns
        -------
        tuple
            Both, the date when the requested EntityModel fiscal year quarter start and end date as a tuple.
            The start date will be first.

        """
        if fy_start_month:
            self.validate_month(fy_start_month)
        self.validate_quarter(quarter)
        qs = self.get_quarter_start(year, quarter, fy_start_month)
        qe = self.get_quarter_end(year, quarter, fy_start_month)
        return qs, qe

    def get_fy_for_date(self, dt: Union[date, datetime], as_str: bool = False) -> Union[str, int]:
        """
        Given a known date, returns the EntityModel fiscal year associated with the given date.

        Parameters
        __________

        dt: date
            Date to evaluate.

        as_str: bool
            If True, return date as a string.


        Returns
        _______
        str or date
            Fiscal year as an integer or string, depending on as_str parameter.
        """
        fy_start_month = self.get_fy_start_month()
        if dt.month >= fy_start_month:
            y = dt.year
        else:
            y = dt.year - 1
        if as_str:
            return str(y)
        return y


class ClosingEntryMixIn:

    def get_closing_entry_digest(self,
                                 to_date: Union[date, datetime],
                                 from_date: Optional[Union[date, datetime]] = None,
                                 user_model: Optional[UserModel] = None,
                                 txs_queryset: Optional[QuerySet] = None,
                                 **kwargs: Dict) -> List:
        io_digest: IODigestContextManager = self.digest(
            user_model=user_model,
            to_date=to_date,
            from_date=from_date,
            txs_queryset=txs_queryset,
            by_unit=True,
            by_activity=True,
            as_io_digest=True,
            **kwargs
        )
        ce_data = io_digest.get_closing_entry_data()

        ClosingEntryModel = lazy_loader.get_closing_entry_model()
        ce_model_list = [
            ClosingEntryModel(
                entity_model=self,
                account_model_id=ce['account_uuid'],
                unit_model_id=ce['unit_uuid'],
                closing_date=to_date,
                activity=ce['activity'],
                balance=ce['balance']
            ) for ce in ce_data
        ]

        for ce in ce_model_list:
            ce.clean()

        return ce_model_list

    # ---> Closing Entry For Month <---
    def get_closing_entry_digest_for_month(self, year: int, month: int, **kwargs: Dict) -> List:
        _, day_end = monthrange(year, month)
        end_dt = date(year=year, month=month, day=day_end)
        return self.get_closing_entry_digest(to_date=end_dt, **kwargs)

    def get_closing_entry_queryset_for_month(self, year: int, month: int):
        _, end_day = monthrange(year, month)
        clo_date = date(year, month, end_day)
        return self.closingentrymodel_set.filter(closing_date__exact=clo_date)

    def save_closing_entry_for_month(self, year: int, month: int):
        closing_entry_qs = self.get_closing_entry_queryset_for_month(year=year, month=month)
        closing_entry_qs.delete()
        ce_data = self.get_closing_entry_digest_for_month(year=year, month=month)
        ClosingEntryModel = lazy_loader.get_closing_entry_model()
        return ClosingEntryModel.objects.bulk_create(
            objs=ce_data,
            batch_size=100
        )

    # ---> Closing Entry For Fiscal Year <---
    def get_closing_entry_digest_for_fiscal_year(self, fiscal_year: int, **kwargs: Dict) -> List:
        end_dt = getattr(self, 'get_fy_end')(year=fiscal_year)
        return self.get_closing_entry_digest(to_date=end_dt, **kwargs)

    def get_closing_entry_queryset_for_fiscal_year(self, fiscal_year: int):
        end_dt: date = getattr(self, 'get_fy_end')(year=fiscal_year)
        return self.closingentrymodel_set.filter(closing_date__exact=end_dt)

    def save_closing_entry_for_fiscal_year(self, fiscal_year: int):
        closing_entry_qs = self.get_closing_entry_queryset_for_fiscal_year(fiscal_year=fiscal_year)
        closing_entry_qs.delete()
        ce_data = self.get_closing_entry_digest_for_fiscal_year(fiscal_year=fiscal_year)
        ClosingEntryModel = lazy_loader.get_closing_entry_model()
        return ClosingEntryModel.objects.bulk_create(
            objs=ce_data,
            batch_size=100
        )

    # ---> Closing Entry Cache Keys <----
    def get_closing_entry_cache_key_for_month(self, year: int, month: int) -> str:
        _, day_end = monthrange(year, month)
        end_dt = date(year=year, month=month, day=day_end)
        end_dt_str = end_dt.strftime('%Y%m%d')
        return f'closing_entry_{end_dt_str}_{self.uuid}'

    def get_closing_entry_cache_key_for_fiscal_year(self, fiscal_year: int) -> str:
        end_dt: date = getattr(self, 'get_fy_end')(year=fiscal_year)
        end_dt_str = end_dt.strftime('%Y%m%d')
        return f'closing_entry_{end_dt_str}_{self.uuid}'

    # ----> Closing Entry Caching < -----

    def get_closing_entry_cache_fiscal_year(self,
                                            fiscal_year: int,
                                            cache_name: str = 'default',

                                            **kwargs):
        cache_system = caches[cache_name]
        ce_cache_key = self.get_closing_entry_cache_key_for_fiscal_year(fiscal_year=fiscal_year)
        ce_ser = cache_system.get(ce_cache_key)
        if ce_ser:
            ce_qs_serde_gen = serializers.deserialize(format='json', stream_or_string=ce_ser)
            return list(ce.object for ce in ce_qs_serde_gen)

        return self.save_closing_entry_cache_fiscal_year(fiscal_year=fiscal_year, cache_name=cache_name, **kwargs)

    def save_closing_entry_cache_fiscal_year(self,
                                             fiscal_year: int,
                                             cache_name: str = 'default',
                                             timeout: Optional[int] = None):
        cache_system = caches[cache_name]
        ce_qs = self.get_closing_entry_queryset_for_fiscal_year(fiscal_year=fiscal_year)
        ce_cache_key = self.get_closing_entry_cache_key_for_fiscal_year(fiscal_year=fiscal_year)
        ce_ser = serializers.serialize(format='json', queryset=ce_qs)

        if not timeout:
            timeout = DJANGO_LEDGER_DEFAULT_CLOSING_ENTRY_CACHE_TIMEOUT

        cache_system.set(ce_cache_key, ce_ser, timeout)
        return list(ce_qs)


class EntityModelAbstract(MP_Node,
                          SlugNameMixIn,
                          CreateUpdateMixIn,
                          ContactInfoMixIn,
                          IOMixIn,
                          LoggingMixIn,
                          FiscalPeriodMixIn,
                          ClosingEntryMixIn):
    """
    The base implementation of the EntityModel. The EntityModel represents the Company, Corporation, Legal Entity,
    Enterprise or Person that engage and operate as a business. The base model inherit from the Materialized Path Node
    of the Django Treebeard library. This allows for complex parent/child relationships between Entities to be tracked
    and managed properly.

    The EntityModel also inherits functionality from the following MixIns:

        1. :func:`SlugNameMixIn <django_ledger.models.mixins.SlugNameMixIn>`
        2. :func:`PaymentTermsMixIn <django_ledger.models.mixins.PaymentTermsMixIn>`
        3. :func:`ContactInfoMixIn <django_ledger.models.mixins.ContactInfoMixIn>`
        4. :func:`CreateUpdateMixIn <django_ledger.models.mixins.CreateUpdateMixIn>`
        5. :func:`EntityReportMixIn <django_ledger.models.mixins.EntityReportMixIn>`
        6. :func:`IOMixIn <django_ledger.io.io_mixin.IOMixIn>`


    Attributes
    __________
    uuid : UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().

    name: str
        The name of the Company, Enterprise, Person, etc. used to identify the Entity.

    admin: UserModel
        The Django UserModel that will be assigned as the administrator of the EntityModel.

    default_coa: ChartOfAccounts
        The default Chart of Accounts Model of the Entity. EntityModel can have multiple Chart of Accounts but only one
        can be assigned as default.

    managers: UserModel
        The Django UserModels that will be assigned as the managers of the EntityModel by the admin.

    hidden: bool
        A flag used to hide the EntityModel from QuerySets. Defaults to False.

    accrual_method: bool
        A flag used to define which method of accounting will be used to produce financial statements.
            * If False, Cash Method of Accounting will be used.
            * If True, Accrual Method of Accounting will be used.

    fy_start_month: int
        An integer that specifies the month that the Fiscal Year starts.

    picture
        The image or logo used to identify the company on reports or UI/UX.
    """

    CASH_METHOD = 'cash'
    ACCRUAL_METHOD = 'accrual'
    FY_MONTHS = [
        (1, _('January')),
        (2, _('February')),
        (3, _('March')),
        (4, _('April')),
        (5, _('May')),
        (6, _('June')),
        (7, _('July')),
        (8, _('August')),
        (9, _('September')),
        (10, _('October')),
        (11, _('November')),
        (12, _('December')),
    ]
    LOGGER_NAME_ATTRIBUTE = 'slug'

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=150, verbose_name=_('Entity Name'))
    default_coa = models.OneToOneField('django_ledger.ChartOfAccountModel',
                                       verbose_name=_('Default Chart of Accounts'),
                                       blank=True,
                                       null=True,
                                       on_delete=models.PROTECT)
    admin = models.ForeignKey(UserModel,
                              on_delete=models.CASCADE,
                              related_name='admin_of',
                              verbose_name=_('Admin'))
    managers = models.ManyToManyField(UserModel,
                                      through='EntityManagementModel',
                                      related_name='managed_by',
                                      verbose_name=_('Managers'))

    hidden = models.BooleanField(default=False)
    accrual_method = models.BooleanField(default=False, verbose_name=_('Use Accrual Method'))
    fy_start_month = models.IntegerField(choices=FY_MONTHS, default=1, verbose_name=_('Fiscal Year Start'))
    last_closing_date = models.DateField(null=True, blank=True, verbose_name=_('Last Closing Entry Date'))
    picture = models.ImageField(blank=True, null=True)
    objects = EntityModelManager.from_queryset(queryset_class=EntityModelQuerySet)()

    node_order_by = ['uuid']

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Entity')
        verbose_name_plural = _('Entities')
        indexes = [
            models.Index(fields=['admin'])
        ]

    def __str__(self):
        return f'EntityModel {self.slug}: {self.name}'

    # ## Logging ###
    def get_logger_name(self):
        return f'EntityModel {self.uuid}'

    # ## ENTITY CREATION ###
    @classmethod
    def create_entity(cls,
                      name: str,
                      use_accrual_method: bool,
                      admin: UserModel,
                      fy_start_month: int,
                      parent_entity=None):
        """
        Convenience Method to Create a new Entity Model. This is the preferred method to create new Entities in order
        to properly handle potential parent/child relationships between EntityModels.

        Parameters
        ----------
        name: str
            The name of the new Entity.
        use_accrual_method: bool
            If True, accrual method of accounting will be used, otherwise Cash Method of accounting will be used.
        fy_start_month: int
            The month which represents the start of a new fiscal year. 1 represents January, 12 represents December.
        admin: UserModel
            The administrator of the new EntityModel.
        parent_entity: EntityModel
            The parent Entity Model of the newly created Entity. If provided, the admin user must also be admin of the
            parent company.

        Returns
        -------

        """
        entity_model = cls(
            name=name,
            accrual_method=use_accrual_method,
            fy_start_month=fy_start_month,
            admin=admin
        )
        entity_model.clean()
        entity_model = cls.add_root(instance=entity_model)
        if parent_entity:
            if isinstance(parent_entity, str):
                # get by slug...
                try:
                    parent_entity_model = EntityModel.objects.get(slug__exact=parent_entity, admin=admin)
                except ObjectDoesNotExist:
                    raise EntityModelValidationError(
                        message=_(
                            f'Invalid Parent Entity. '
                            f'Entity with slug {parent_entity} is not administered by {admin.username}')
                    )
            elif isinstance(parent_entity, UUID):
                # get by uuid...
                try:
                    parent_entity_model = EntityModel.objects.get(uuid__exact=parent_entity, admin=admin)
                except ObjectDoesNotExist:
                    raise EntityModelValidationError(
                        message=_(
                            f'Invalid Parent Entity. '
                            f'Entity with UUID {parent_entity} is not administered by {admin.username}')
                    )
            elif isinstance(parent_entity, cls):
                # EntityModel instance provided...
                if parent_entity.admin != admin:
                    raise EntityModelValidationError(
                        message=_(
                            f'Invalid Parent Entity. '
                            f'Entity {parent_entity} is not administered by {admin.username}')
                    )
                parent_entity_model = parent_entity
            else:
                raise EntityModelValidationError(
                    _('Only slug, UUID or EntityModel allowed.')
                )

            parent_entity.add_child(instance=entity_model)
        return entity_model

    # ### ACCRUAL METHODS ######
    def get_accrual_method(self) -> str:
        if self.is_cash_method():
            return self.CASH_METHOD
        return self.ACCRUAL_METHOD

    def is_cash_method(self) -> bool:
        return self.accrual_method is False

    def is_accrual_method(self) -> bool:
        return self.accrual_method is True

    def is_admin_user(self, user_model):
        return user_model.id == self.admin_id

    # #### SLUG GENERATION ###
    @staticmethod
    def generate_slug_from_name(name: str) -> str:
        """
        Uses Django's slugify function to create a valid slug from any given string.

        Parameters
        ----------
        name: str
            The name or string to slugify.

        Returns
        -------
            The slug as a String.
        """
        slug = slugify(name)
        suffix = ''.join(choices(ENTITY_RANDOM_SLUG_SUFFIX, k=8))
        entity_slug = f'{slug}-{suffix}'
        return entity_slug

    def generate_slug(self,
                      commit: bool = False,
                      raise_exception: bool = True,
                      force_update: bool = False) -> str:
        """
        Convenience method to create the EntityModel slug.

        Parameters
        ----------
        force_update: bool
            If True, will update the EntityModel slug.

        raise_exception: bool
            Raises ValidationError if EntityModel already has a slug.

        commit: bool
            If True,
        """
        if not force_update and self.slug:
            if raise_exception:
                raise ValidationError(
                    message=_(f'Cannot replace existing slug {self.slug}. Use force_update=True if needed.')
                )

        self.slug = self.generate_slug_from_name(self.name)

        if commit:
            self.save(update_fields=[
                'slug',
                'updated'
            ])
        return self.slug

    # #### CHART OF ACCOUNTS ####
    def has_default_coa(self) -> bool:
        """
        Determines if the EntityModel instance has a Default CoA.

        Returns
        -------
        bool
            True if EntityModel instance has a Default CoA.
        """
        return self.default_coa_id is not None

    def get_default_coa(self, raise_exception: bool = True) -> Optional[ChartOfAccountModel]:
        """
        Fetches the EntityModel default Chart of Account.

        Parameters
        ----------
        raise_exception: bool
            Raises exception if no default CoA has been assigned.

        Returns
        -------
        ChartOfAccountModel
            The EntityModel default ChartOfAccount.
        """

        if not self.default_coa_id:
            if raise_exception:
                raise EntityModelValidationError(f'EntityModel {self.slug} does not have a default CoA')
        return self.default_coa

    def create_chart_of_accounts(self,
                                 assign_as_default: bool = False,
                                 coa_name: Optional[str] = None,
                                 commit: bool = False) -> ChartOfAccountModel:
        """
        Creates a Chart of Accounts for the Entity Model and optionally assign it as the default Chart of Accounts.
        EntityModel must have a default Chart of Accounts before being able to transact.

        Parameters
        ----------
        coa_name: str
            The new CoA name. If not provided will be auto generated based on the EntityModel name.

        commit: bool
            Commits the transaction into the DB. A ChartOfAccountModel will

        assign_as_default: bool
            Assigns the newly created ChartOfAccountModel as the EntityModel default_coa.

        Returns
        -------
        ChartOfAccountModel
            The newly created chart of accounts model.
        """
        # todo: this logic will generate always the same slug...
        if not coa_name:
            coa_name = 'Default CoA'

        chart_of_accounts = ChartOfAccountModel(
            slug=self.slug + ''.join(choices(ENTITY_RANDOM_SLUG_SUFFIX, k=6)) + '-coa',
            name=coa_name,
            entity=self
        )
        chart_of_accounts.clean()
        chart_of_accounts.save()
        chart_of_accounts.configure()

        if assign_as_default:
            self.default_coa = chart_of_accounts
            if commit:
                self.save(update_fields=[
                    'default_coa',
                    'updated'
                ])
        return chart_of_accounts

    def populate_default_coa(self,
                             activate_accounts: bool = False,
                             force: bool = False,
                             ignore_if_default_coa: bool = True,
                             coa_model: Optional[ChartOfAccountModel] = None,
                             commit: bool = True):
        """
        Populates the EntityModel default CoA with the default Chart of Account list provided by Django Ledger or user
        defined. See DJANGO_LEDGER_DEFAULT_COA setting.

        Parameters
        ----------
        activate_accounts: bool
            Activates all AccountModels for immediate use. Defaults to False.
        force: bool
            Forces the creation of accounts even if other accounts are present. Defaults to False.
        ignore_if_default_coa: bool
            Raises exception if EntityModel already has a default CoA. Defaults to True.
        coa_model: ChartOfAccountModel
            Optional CoA Model to populate. Will be validated against EntityModel if provided.
        commit: bool
        '   Commits the newly created CoA into the Database. Defaults to True.
        """

        if not coa_model:
            if not self.has_default_coa():
                self.create_chart_of_accounts(assign_as_default=True, commit=commit)
            coa_model: ChartOfAccountModel = self.default_coa
        else:
            self.validate_chart_of_accounts_for_entity(coa_model=coa_model)

        coa_accounts_qs = coa_model.accountmodel_set.all()

        # forces evaluation
        len(coa_accounts_qs)

        coa_has_accounts = coa_accounts_qs.not_coa_root().exists()

        if not coa_has_accounts or force:
            root_accounts = coa_accounts_qs.is_coa_root()

            root_maps = {
                root_accounts.get(role__exact=k): [
                    AccountModel(
                        code=a['code'],
                        name=a['name'],
                        role=a['role'],
                        balance_type=a['balance_type'],
                        active=activate_accounts,
                        # coa_model=chart_of_accounts,
                    ) for a in v] for k, v in CHART_OF_ACCOUNTS_ROOT_MAP.items()
            }

            for root_acc, acc_model_list in root_maps.items():
                roles_set = set(account_model.role for account_model in acc_model_list)
                for i, account_model in enumerate(acc_model_list):
                    account_model.role_default = True if account_model.role in roles_set else False

                    try:
                        roles_set.remove(account_model.role)
                    except KeyError:
                        pass

                    account_model.clean()
                    coa_model.create_account(account_model)

        else:
            if not ignore_if_default_coa:
                raise EntityModelValidationError(f'Entity {self.name} already has existing accounts. '
                                                 'Use force=True to bypass this check')

    # Model Validators....
    def validate_chart_of_accounts_for_entity(self,
                                              coa_model: ChartOfAccountModel,
                                              raise_exception: bool = True) -> bool:
        """
        Validates the CoA Model against the EntityModel instance.

        Parameters
        ----------
        coa_model: ChartOfAccountModel
            The CoA Model to validate.
        raise_exception: bool
            Raises EntityModelValidationError if CoA Model is not valid for the EntityModel instance.

        Returns
        -------
        bool
            True if valid, else False.
        """
        if coa_model.entity_id == self.uuid:
            return True
        if raise_exception:
            raise EntityModelValidationError(
                f'Invalid ChartOfAccounts model {coa_model.slug} for EntityModel {self.slug}')
        return False

    def validate_account_model_for_coa(self,
                                       account_model: AccountModel,
                                       coa_model: ChartOfAccountModel,
                                       raise_exception: bool = True) -> bool:
        """
        Validates that the AccountModel provided belongs to the CoA Model provided.

        Parameters
        ----------
        account_model: AccountModel
            The AccountModel to validate.
        coa_model: ChartOfAccountModel
            The ChartOfAccountModel to validate against.
        raise_exception: bool
            Raises EntityModelValidationError if AccountModel is invalid for the EntityModel and CoA instance.

        Returns
        -------
        bool
            True if valid, else False.
        """
        valid = self.validate_chart_of_accounts_for_entity(coa_model, raise_exception=raise_exception)
        if not valid:
            return valid
        if valid and account_model.coa_model_id == coa_model.uuid:
            return True
        if raise_exception:
            raise EntityModelValidationError(
                f'Invalid AccountModel model {account_model.uuid} for EntityModel {self.slug}'
            )
        return False

    @staticmethod
    def validate_account_model_for_role(account_model: AccountModel, role: str):
        if account_model.role != role:
            raise EntityModelValidationError(f'Invalid account role: {account_model.role}, expected {role}')

    def validate_ledger_model_for_entity(self, ledger_model: Union[LedgerModel, UUID, str]):
        if ledger_model.entity_id != self.uuid:
            raise EntityModelValidationError(f'Invalid LedgerModel {ledger_model.uuid} for entity {self.slug}')

    def get_all_coa_accounts(self,
                             order_by: Optional[Tuple[str]] = ('code',),
                             active: bool = True) -> Tuple[
        ChartOfAccountModelQuerySet, Dict[ChartOfAccountModel, AccountModelQuerySet]]:

        """
        Fetches all the AccountModels associated with the EntityModel grouped by ChartOfAccountModel.

        Parameters
        ----------
        active: bool
            Selects only active accounts.
        order_by: list of strings.
            Optional list of fields passed to the order_by QuerySet method.

        Returns
        -------
        Tuple: Tuple[ChartOfAccountModelQuerySet, Dict[ChartOfAccountModel, AccountModelQuerySet]
            The ChartOfAccountModelQuerySet and a grouping of AccountModels by ChartOfAccountModel as keys.
        """

        account_model_qs = ChartOfAccountModel.objects.filter(
            entity_id=self.uuid
        ).select_related('entity').prefetch_related('accountmodel_set')

        return account_model_qs, {
            coa_model: coa_model.accountmodel_set.filter(active=active).order_by(*order_by) for coa_model in
            account_model_qs
        }

    # ##### ACCOUNT MANAGEMENT ######
    def get_all_accounts(self, active: bool = True, order_by: Optional[Tuple[str]] = ('code',)) -> AccountModelQuerySet:
        """
        Fetches all AccountModelQuerySet associated with the EntityModel.

        Parameters
        ----------
        active: bool
            Selects only active accounts.
        order_by: list of strings.
            Optional list of fields passed to the order_by QuerySet method.
        Returns
        -------
        AccountModelQuerySet
            The AccountModelQuerySet of the assigned default CoA.
        """

        account_model_qs = AccountModel.objects.filter(
            coa_model__entity__uuid__exact=self.uuid
        ).select_related('coa_model', 'coa_model__entity')

        if active:
            account_model_qs = account_model_qs.active()
        if order_by:
            account_model_qs = account_model_qs.order_by(*order_by)
        return account_model_qs

    def get_coa_accounts(self,
                         coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                         active: bool = True,
                         order_by: Optional[Tuple] = ('code',)) -> AccountModelQuerySet:
        """
        Fetches the AccountModelQuerySet for a specific ChartOfAccountModel.

        Parameters
        ----------
        coa_model: ChartOfAccountModel, UUID, str
            The ChartOfAccountsModel UUID, model instance or slug to pull accounts from. If None, will use default CoA.
        active: bool
            Selects only active accounts.
        order_by: list of strings.
            Optional list of fields passed to the order_by QuerySet method.

        Returns
        -------
        AccountModelQuerySet
            The AccountModelQuerySet of the assigned default CoA.
        """

        if not coa_model:
            account_model_qs = self.default_coa.accountmodel_set.all().select_related('coa_model', 'coa_model__entity')
        else:
            account_model_qs = AccountModel.objects.filter(
                coa_model__entity__uuid__exact=self.uuid
            ).select_related('coa_model', 'coa_model__entity')

            if isinstance(coa_model, ChartOfAccountModel):
                self.validate_chart_of_accounts_for_entity(coa_model=coa_model, raise_exception=True)
                account_model_qs = coa_model.accountmodel_set.all()
            if isinstance(coa_model, str):
                account_model_qs = account_model_qs.filter(coa_model__slug__exact=coa_model)
            elif isinstance(coa_model, UUID):
                account_model_qs = account_model_qs.filter(coa_model__uuid__exact=coa_model)

        if active:
            account_model_qs = account_model_qs.active()

        if order_by:
            account_model_qs = account_model_qs.order_by(*order_by)

        return account_model_qs

    def get_default_coa_accounts(self,
                                 active: bool = True,
                                 order_by: Optional[Tuple[str]] = ('code',),
                                 raise_exception: bool = True) -> Optional[AccountModelQuerySet]:
        """
        Fetches the default AccountModelQuerySet.

        Parameters
        ----------
        active: bool
            Selects only active accounts.
        order_by: list of strings.
            Optional list of fields passed to the order_by QuerySet method.
        raise_exception: bool
            Raises EntityModelValidationError if no default_coa found.

        Returns
        -------
        AccountModelQuerySet
            The AccountModelQuerySet of the assigned default CoA.
        """
        if not self.default_coa_id:
            if raise_exception:
                raise EntityModelValidationError(message=_('No default_coa found.'))
            return

        return self.get_coa_accounts(active=active, order_by=order_by)

    def get_accounts_with_codes(self,
                                code_list: Union[str, List[str]],
                                coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None
                                ) -> AccountModelQuerySet:
        """
        Fetches the AccountModelQuerySet with provided code list.

        Parameters
        ----------
        coa_model: ChartOfAccountModel, UUID, str
            The ChartOfAccountsModel UUID, model instance or slug to pull accounts from. Uses default Coa if not
            provided.
        code_list: list or str
            Code or list of codes to fetch.

        Returns
        -------
        AccountModelQuerySet
            The requested AccountModelQuerySet with applied code filter.
        """

        if not coa_model:
            account_model_qs = self.get_default_coa_accounts()
        else:
            account_model_qs = self.get_coa_accounts(coa_model=coa_model)

        if isinstance(code_list, str):
            return account_model_qs.filter(code__exact=code_list)
        return account_model_qs.filter(code__in=code_list)

    def get_default_account_for_role(self,
                                     role: str,
                                     coa_model: Optional[ChartOfAccountModel] = None) -> AccountModel:
        """
        Gets the given role default AccountModel from the provided CoA.
        CoA will be validated against the EntityModel instance.

        Parameters
        ----------
        role: str
            The CoA role to fetch the corresponding default Account Model.
        coa_model: ChartOfAccountModel
            The CoA Model to pull default account from. If not provided, will use EntityModel default CoA.

        Returns
        -------
        AccountModel
            The default account model for the specified CoA role.
        """
        validate_roles(role, raise_exception=True)
        if not coa_model:
            coa_model = self.default_coa
        else:
            self.validate_chart_of_accounts_for_entity(coa_model)

        account_model_qs = coa_model.accountmodel_set.all().is_role_default()
        return account_model_qs.get(role__exact=role)

    def create_account(self,
                       account_model_kwargs: Dict,
                       coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                       raise_exception: bool = True) -> Tuple[ChartOfAccountModel, AccountModel]:
        """
        Creates a new AccountModel for the EntityModel.

        Parameters
        ----------
        coa_model: ChartOfAccountModel, UUID, str
            The ChartOfAccountsModel UUID, model instance or slug to pull accounts from. Uses default Coa if not
            provided.
        account_model_kwargs: dict
            A dictionary of kwargs to be used to create the new AccountModel instance.
        raise_exception: bool
            Raises EntityModelValidationError if ChartOfAccountsModel is not valid for the EntityModel instance.

        Returns
        -------
        A tuple of ChartOfAccountModel, AccountModel
            The ChartOfAccountModel and AccountModel instance just created.
        """
        if coa_model:
            if isinstance(coa_model, UUID):
                coa_model = self.chartofaccountsmodel_set.get(uuid__exact=coa_model)
            elif isinstance(coa_model, str):
                coa_model = self.chartofaccountsmodel_set.get(slug__exact=coa_model)
            elif isinstance(coa_model, ChartOfAccountModel):
                self.validate_chart_of_accounts_for_entity(coa_model=coa_model, raise_exception=raise_exception)
        else:
            coa_model = self.default_coa

        account_model = AccountModel(**account_model_kwargs)
        account_model.clean()
        return coa_model, coa_model.create_account(account_model=account_model)

    # ### VENDOR MANAGEMENT ####
    def get_vendors(self, active: bool = True) -> VendorModelQuerySet:
        """
        Fetches the VendorModels associated with the EntityModel instance.

        Parameters
        ----------
        active: bool
            Active VendorModels only. Defaults to True.

        Returns
        -------
        VendorModelQuerySet
            The EntityModel instance VendorModelQuerySet with applied filters.
        """
        vendor_qs = self.vendormodel_set.all().select_related('entity_model')
        if active:
            vendor_qs = vendor_qs.active()
        return vendor_qs

    def get_vendor_by_number(self, vendor_number: str):
        vendor_model_qs = self.get_vendors()
        return vendor_model_qs.get(vendor_number__exact=vendor_number)

    def get_vendor_by_uuid(self, vendor_uuid: Union[str, UUID]):
        vendor_model_qs = self.get_vendors()
        return vendor_model_qs.get(uuid__exact=vendor_uuid)

    def create_vendor(self, vendor_model_kwargs: Dict, commit: bool = True) -> VendorModel:
        """
        Creates a new VendorModel associated with the EntityModel instance.

        Parameters
        ----------
        vendor_model_kwargs: dict
            The kwargs to be used for the new VendorModel.
        commit: bool
            Saves the VendorModel instance in the Database.

        Returns
        -------
        VendorModel
        """
        vendor_model = VendorModel(entity_model=self, **vendor_model_kwargs)
        vendor_model.clean()
        if commit:
            vendor_model.save()
        return vendor_model

    # ### CUSTOMER MANAGEMENT ####

    def get_customers(self, active: bool = True) -> CustomerModelQueryset:
        """
        Fetches the CustomerModel associated with the EntityModel instance.

        Parameters
        ----------
        active: bool
            Active CustomerModel only. Defaults to True.

        Returns
        -------
        CustomerModelQueryset
            The EntityModel instance CustomerModelQueryset with applied filters.
        """
        customer_model_qs = self.customermodel_set.all().select_related('entity_model')
        if active:
            customer_model_qs = customer_model_qs.active()
        return customer_model_qs

    def get_customer_by_number(self, customer_number: str):
        customer_model_qs = self.get_customers()
        return customer_model_qs.get(customer_number__exact=customer_number)

    def get_customer_by_uuid(self, customer_uuid: Union[str, UUID]):
        customer_model_qs = self.get_customers()
        return customer_model_qs.get(uuid__exact=customer_uuid)

    def validate_customer(self, customer_model: CustomerModel):
        if customer_model.entity_model_id != self.uuid:
            raise EntityModelValidationError(f'Invalid CustomerModel {self.uuid} for EntityModel {self.uuid}...')

    def create_customer(self, customer_model_kwargs: Dict, commit: bool = True) -> CustomerModel:
        """
        Creates a new CustomerModel associated with the EntityModel instance.

        Parameters
        ----------
        customer_model_kwargs: dict
            The kwargs to be used for the new CustomerModel.
        commit: bool
            Saves the CustomerModel instance in the Database.

        Returns
        -------
        CustomerModel
        """
        customer_model = CustomerModel(entity_model=self, **customer_model_kwargs)
        customer_model.clean()
        if commit:
            customer_model.save()
        return customer_model

    # ### BILL MANAGEMENT ####
    def get_bills(self):
        """
        Fetches a QuerySet of BillModels associated with the EntityModel instance.

        Returns
        -------
        BillModelQuerySet
        """
        BillModel = lazy_loader.get_bill_model()
        return BillModel.objects.filter(
            ledger__entity__uuid__exact=self.uuid
        ).select_related('ledger', 'ledger__entity', 'vendor')

    def create_bill(self,
                    vendor_model: Union[VendorModel, UUID, str],
                    terms: str,
                    date_draft: Optional[date] = None,
                    xref: Optional[str] = None,
                    cash_account: Optional[AccountModel] = None,
                    prepaid_account: Optional[AccountModel] = None,
                    payable_account: Optional[AccountModel] = None,
                    additional_info: Optional[Dict] = None,
                    ledger_name: Optional[str] = None,
                    coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                    commit: bool = True):
        """
        Creates a new BillModel for the EntityModel instance.
        Bill will have DRAFT status.

        Parameters
        ----------
        vendor_model: VendorModel or UUID or str
            The VendorModel, VendorModel UUID or VendorModel Number
        terms: str
            Payment terms of the new BillModel. A choice of BillModel.TERM_CHOICES_VALID
        date_draft: date
            Date to use as draft date for the new BillModel.
        xref: str
            Optional External Reference for the Bill (i.e. Vendor invoice number.)
        cash_account: AccountModel
            Optional CASH AccountModel associated with the new BillModel. Defaults to CASH default AccountModel role.
        prepaid_account: AccountModel
            Optional PREPAID AccountModel associated with the new BillModel for accruing purposes.
            Defaults to PREPAID default AccountModel role.
        payable_account: AccountModel
            Optional PAYABLE AccountModel associated with the new BillModel for accruing purposes.
            Defaults to ACCOUNTS PAYABLE default AccountModel role.
        additional_info: Dict
            Additional user-defined information stored as JSON in the Database.
        ledger_name: str
            Optional LedgerModel name to be assigned to the BillModel instance.
        coa_model: ChartOfAccountModel
            Optional ChartOfAccountsModel to use when fetching default role AccountModels
        commit: bool
            If True, commits the new BillModel in the Database.

        Returns
        -------
        BillModel
            The newly created BillModel in DRAFT state.
        """
        BillModel = lazy_loader.get_bill_model()

        if isinstance(vendor_model, VendorModel):
            if not vendor_model.entity_model_id == self.uuid:
                raise EntityModelValidationError(f'VendorModel {vendor_model.uuid} belongs to a different EntityModel.')
        elif isinstance(vendor_model, UUID):
            vendor_model = self.get_vendor_by_uuid(vendor_uuid=vendor_model)
        elif isinstance(vendor_model, str):
            vendor_model = self.get_vendor_by_number(vendor_number=vendor_model)
        else:
            raise EntityModelValidationError('VendorModel must be an instance of VendorModel, UUID or str.')

        account_model_qs = self.get_coa_accounts(coa_model=coa_model, active=True)

        account_model_qs = account_model_qs.with_roles(roles=[
            roles_module.ASSET_CA_CASH,
            roles_module.ASSET_CA_PREPAID,
            roles_module.LIABILITY_CL_ACC_PAYABLE
        ]).is_role_default()

        # evaluates the queryset...
        len(account_model_qs)

        bill_model = BillModel(
            xref=xref,
            vendor=vendor_model,
            terms=terms,
            additional_info=additional_info,
            cash_account=account_model_qs.get(role=roles_module.ASSET_CA_CASH) if not cash_account else cash_account,
            prepaid_account=account_model_qs.get(
                role=roles_module.ASSET_CA_PREPAID) if not prepaid_account else prepaid_account,
            unearned_account=account_model_qs.get(
                role=roles_module.LIABILITY_CL_ACC_PAYABLE) if not payable_account else payable_account
        )

        _, bill_model = bill_model.configure(entity_slug=self,
                                             ledger_name=ledger_name,
                                             date_draft=date_draft,
                                             commit=commit,
                                             commit_ledger=commit)

        return bill_model

    def get_items_for_bill(self) -> ItemModelQuerySet:
        item_model_qs: ItemModelQuerySet = self.itemmodel_set.all()
        return item_model_qs.select_related('uom', 'entity').bills()

    # ### INVOICE MANAGEMENT ####
    def get_invoices(self):
        """
        Fetches a QuerySet of InvoiceModels associated with the EntityModel instance.

        Returns
        -------
        InvoiceModelQuerySet
        """
        InvoiceModel = lazy_loader.get_invoice_model()
        return InvoiceModel.objects.filter(
            ledger__entity__uuid__exact=self.uuid
        ).select_related('ledger', 'ledger__entity', 'customer')

    def create_invoice(self,
                       customer_model: Union[VendorModel, UUID, str],
                       terms: str,
                       cash_account: Optional[AccountModel] = None,
                       prepaid_account: Optional[AccountModel] = None,
                       payable_account: Optional[AccountModel] = None,
                       additional_info: Optional[Dict] = None,
                       ledger_name: Optional[str] = None,
                       coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                       date_draft: Optional[date] = None,
                       commit: bool = True):

        """
        Creates a new InvoiceModel for the EntityModel instance.
        Invoice will have DRAFT status.

        Parameters
        ----------
        customer_model: CustomerModel or UUID or str
            The CustomerModel, CustomerModel UUID or CustomerModel Number
        terms: str
            A choice of InvoiceModel.TERM_CHOICES_VALID
        cash_account: AccountModel
            Optional CASH AccountModel associated with the new InvoiceModel. Defaults to CASH default AccountModel role.
        prepaid_account: AccountModel
            Optional PREPAID AccountModel associated with the new InvoiceModel for accruing purposes.
            Defaults to PREPAID default AccountModel role.
        payable_account: AccountModel
            Optional PAYABLE AccountModel associated with the new InvoiceModel for accruing purposes.
            Defaults to ACCOUNTS PAYABLE default AccountModel role.
        additional_info: Dict
            Additional user-defined information stored as JSON in the Database.
        ledger_name: str
            Optional LedgerModel name to be assigned to the InvoiceModel instance.
        coa_model: ChartOfAccountModel
            Optional ChartOfAccountsModel to use when fetching default role AccountModels
        date_draft: date
            Optional date to use as Draft Date. Defaults to localdate() if None.
        commit: bool
            If True, commits the new BillModel in the Database.

        Returns
        -------
        InvoiceModel
            The newly created InvoiceModel in DRAFT state.
        """
        InvoiceModel = lazy_loader.get_invoice_model()

        if isinstance(customer_model, CustomerModel):
            if not customer_model.entity_model_id == self.uuid:
                raise EntityModelValidationError(
                    f'CustomerModel {customer_model.uuid} belongs to a different EntityModel.')
        elif isinstance(customer_model, UUID):
            customer_model = self.get_customer_by_uuid(customer_uuid=customer_model)
        elif isinstance(customer_model, str):
            customer_model = self.get_customer_by_number(customer_number=customer_model)
        else:
            raise EntityModelValidationError('CustomerModel must be an instance of CustomerModel, UUID or str.')

        account_model_qs = self.get_coa_accounts(coa_model=coa_model, active=True)
        account_model_qs = account_model_qs.with_roles(roles=[
            roles_module.ASSET_CA_CASH,
            roles_module.ASSET_CA_PREPAID,
            roles_module.LIABILITY_CL_ACC_PAYABLE
        ]).is_role_default()

        # evaluates the queryset...
        len(account_model_qs)

        invoice_model = InvoiceModel(
            customer=customer_model,
            additional_info=additional_info,
            terms=terms,
            cash_account=account_model_qs.get(role=roles_module.ASSET_CA_CASH) if not cash_account else cash_account,
            prepaid_account=account_model_qs.get(
                role=roles_module.ASSET_CA_PREPAID) if not prepaid_account else prepaid_account,
            unearned_account=account_model_qs.get(
                role=roles_module.LIABILITY_CL_ACC_PAYABLE) if not payable_account else payable_account
        )

        _, invoice_model = invoice_model.configure(entity_slug=self,
                                                   ledger_name=ledger_name,
                                                   commit=commit,
                                                   date_draft=date_draft,
                                                   commit_ledger=commit)

        return invoice_model

    # ### PURCHASE ORDER MANAGEMENT ####
    def get_purchase_orders(self):
        """
        Fetches a QuerySet of PurchaseOrderModels associated with the EntityModel instance.

        Returns
        -------
        PurchaseOrderModelQuerySet
        """
        return self.purchaseordermodel_set.all().select_related('entity')

    def create_purchase_order(self,
                              po_title: Optional[str] = None,
                              estimate_model=None,
                              date_draft: Optional[date] = None,
                              commit: bool = True):
        """
        Creates a new PurchaseOrderModel for the EntityModel instance.
        PO will have DRAFT status.

        Parameters
        ----------
        po_title: str
            The user defined title for the new Purchase Order Model.
        date_draft: date
            Optional date to use as Draft Date. Defaults to localdate() if None.
        estimate_model: EstimateModel
            The EstimateModel to associate the PO for tracking.
        commit: bool
            If True, commits the new PO in the Database. Defaults to True.

        Returns
        -------
        PurchaseOrderModel
            The newly created PurchaseOrderModel in DRAFT state.
        """
        PurchaseOrderModel = lazy_loader.get_purchase_order_model()
        po_model = PurchaseOrderModel()
        return po_model.configure(
            entity_slug=self,
            draft_date=date_draft,
            estimate_model=estimate_model,
            commit=commit,
            po_title=po_title
        )

    # ### ESTIMATE/CONTRACT MANAGEMENT ####
    def get_estimates(self):
        """
        Fetches a QuerySet of EstimateModels associated with the EntityModel instance.

        Returns
        -------
        EstimateModelQuerySet
        """
        return self.estimatemodel_set.all().select_related('entity')

    def create_estimate(self,
                        estimate_title: str,
                        contract_terms: str,
                        customer_model: Union[CustomerModel, UUID, str],
                        date_draft: Optional[date] = None,
                        commit: bool = True):
        """
        Creates a new EstimateModel for the EntityModel instance.
        Estimate will have DRAFT status.

        Parameters
        ----------
        estimate_title: str
            A user defined title for the Estimate.
        date_draft: date
            Optional date to use as Draft Date. Defaults to localdate() if None.
        customer_model: CustomerModel or UUID or str
            The CustomerModel, CustomerModel UUID or CustomerModel Number
        contract_terms: str
            A choice of EstimateModel.CONTRACT_TERMS_CHOICES_VALID
        commit: bool
            If True, commits the new PO in the Database. Defaults to True.

        Returns
        -------
        PurchaseOrderModel
            The newly created PurchaseOrderModel in DRAFT state.
        """
        if isinstance(customer_model, CustomerModel):
            self.validate_customer(customer_model)
        elif isinstance(customer_model, str):
            customer_model = self.get_customer_by_number(customer_number=customer_model)
        elif isinstance(customer_model, UUID):
            customer_model = self.get_customer_by_uuid(customer_uuid=customer_model)
        else:
            raise EntityModelValidationError('CustomerModel must be an instance of CustomerModel, UUID or str.')

        EstimateModel = lazy_loader.get_estimate_model()
        estimate_model = EstimateModel(terms=contract_terms)
        return estimate_model.configure(
            entity_slug=self,
            date_draft=date_draft,
            customer_model=customer_model,
            estimate_title=estimate_title,
            commit=commit
        )

    # ### BANK ACCOUNT MANAGEMENT ####
    def get_bank_accounts(self, active: bool = True) -> BankAccountModelQuerySet:
        """
        Fetches a QuerySet of BankAccountModels associated with the EntityModel instance.

        Parameters
        ----------
        active: bool
            If True, returns only active Bank Accounts. Defaults to True.

        Returns
        -------
        BankAccountModelQuerySet
        """
        bank_account_qs = self.bankaccountmodel_set.all().select_related('entity_model')
        if active:
            bank_account_qs = bank_account_qs.active()
        return bank_account_qs

    def create_bank_account(self,
                            name: str,
                            account_type: str,
                            active=False,
                            cash_account: Optional[AccountModel] = None,
                            coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                            bank_account_model_kwargs: Optional[Dict] = None,
                            commit: bool = True):

        """
        Creates a new BankAccountModel for the EntityModel instance.
        Estimate will have DRAFT status.

        Parameters
        ----------
        name: str
            A user defined name for the BankAccountModel.
        account_type: date
            A choice of BankAccountModel.VALID_ACCOUNT_TYPES.
        active: bool
            Marks the account as active.
        cash_account: AccountModel
            Optional CASH AccountModel associated with the new InvoiceModel. Defaults to CASH default AccountModel role.
        coa_model: ChartOfAccountModel
            Optional ChartOfAccountsModel to use when fetching default role AccountModels.
        commit: bool
            If True, commits the new BankAccountModel in the Database. Defaults to True.
        bank_account_model_kwargs: Dict
            Additional kwargs for the new BankAccountModel instance.

        Returns
        -------
        PurchaseOrderModel
            The newly created PurchaseOrderModel in DRAFT state.
        """

        if bank_account_model_kwargs is None:
            bank_account_model_kwargs = dict()
        if account_type not in BankAccountModel.VALID_ACCOUNT_TYPES:
            raise EntityModelValidationError(
                _(f'Invalid Account Type: choices are {BankAccountModel.VALID_ACCOUNT_TYPES}'))
        account_model_qs = self.get_coa_accounts(coa_model=coa_model, active=True)
        account_model_qs = account_model_qs.with_roles(roles=roles_module.ASSET_CA_CASH).is_role_default()
        bank_account_model = BankAccountModel(
            name=name,
            entity_model=self,
            account_type=account_type,
            active=active,
            cash_account=account_model_qs.get() if not cash_account else cash_account,
            **bank_account_model_kwargs
        )
        bank_account_model.clean()
        if commit:
            bank_account_model.save()
        return bank_account_model

    # #### ITEM MANAGEMENT ###
    def validate_item_qs(self, item_qs: ItemModelQuerySet, raise_exception: bool = True) -> bool:
        """
        Validates the given ItemModelQuerySet against the EntityModel instance.
        Parameters
        ----------
        item_qs: ItemModelQuerySet
            The ItemModelQuerySet to validate.
        raise_exception: bool
            Raises EntityModelValidationError if ItemModelQuerySet is not valid.

        Returns
        -------
        bool
            True if valid, else False.
        """
        for item_model in item_qs:
            if item_model.entity_id != self.uuid:
                if raise_exception:
                    raise EntityModelValidationError(f'Invalid item_qs provided for entity {self.slug}...')
                return False
        return True

    def get_uom_all(self) -> UnitOfMeasureModelQuerySet:
        """
        Fetches the EntityModel instance Unit of Measures QuerySet.

        Returns
        -------
        UnitOfMeasureModelQuerySet
        """
        return self.unitofmeasuremodel_set.all().select_related('entity')

    def create_uom(self, name: str, unit_abbr: str, active: bool = True, commit: bool = True) -> UnitOfMeasureModel:
        """
        Creates a new Unit of Measure Model associated with the EntityModel instance

        Parameters
        ----------
        name: str
            The user defined name of the new Unit of Measure Model instance.
        unit_abbr: str
            The unique slug abbreviation of the UoM model. Will be indexed.
        active: bool
            Mark this UoM as active.
        commit: bool
            Saves the model in the DB if True. Defaults to True

        Returns
        -------
        UnitOfMeasureModel
        """
        uom_model = UnitOfMeasureModel(
            name=name,
            unit_abbr=unit_abbr,
            is_active=active,
            entity=self
        )
        uom_model.clean()
        uom_model.clean_fields()
        if commit:
            uom_model.save()
        return uom_model

    def get_items_all(self, active: bool = True) -> ItemModelQuerySet:
        """
        Fetches all EntityModel instance ItemModel's.
        QuerySet selects relevant related fields to avoid additional
        DB queries for most use cases.

        Parameters
        ----------
        active: bool
            Filters the QuerySet to active accounts only. Defaults to True.

        Returns
        -------
        ItemModelQuerySet
        """
        qs = self.itemmodel_set.all().select_related(
            'uom',
            'entity',
            'inventory_account',
            'cogs_account',
            'earnings_account',
            'expense_account'
        )
        if active:
            return qs.active()
        return qs

    def get_items_products(self, active: bool = True) -> ItemModelQuerySet:
        """
        Fetches all EntityModel instance ItemModel's that qualify as Products.
        QuerySet selects relevant related fields to avoid additional
        DB queries for most use cases.

        Parameters
        ----------
        active: bool
            Filters the QuerySet to active accounts only. Defaults to True.

        Returns
        -------
        ItemModelQuerySet
        """
        qs = self.get_items_all(active=active)
        return qs.products()

    def create_item_product(self,
                            name: str,
                            item_type: str,
                            uom_model: Union[UUID, UnitOfMeasureModel],
                            coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                            commit: bool = True) -> ItemModel:
        """
        Creates a new items of type PRODUCT.

        Parameters
        ----------
        name: str
            Name of the new service.
        item_type: str
            The type of product. A choice of ItemModel.ITEM_TYPE_CHOICES
        uom_model:
            The UOM UUID or UnitOfMeasureModel of the Service. Will be validated if provided.
        coa_model: ChartOfAccountModel
            Optional ChartOfAccountsModel to use when fetching default role AccountModels.
        commit: bool
            Commits the ItemModel in the DB. Defaults to True.
        Returns
        -------
        ItemModel
            The created Product.
        """
        if isinstance(uom_model, UUID):
            uom_model = self.unitofmeasuremodel_set.select_related('entity').get(uuid__exact=uom_model)
        elif isinstance(uom_model, UnitOfMeasureModel):
            if uom_model.entity_id != self.uuid:
                raise EntityModelValidationError(f'Invalid UnitOfMeasureModel for entity {self.slug}...')

        account_model_qs = self.get_coa_accounts(coa_model=coa_model, active=True)
        account_model_qs = account_model_qs.with_roles(roles=[
            roles_module.ASSET_CA_INVENTORY,
            roles_module.COGS,
            roles_module.INCOME_OPERATIONAL
        ]).is_role_default()

        # evaluates the queryset...
        len(account_model_qs)

        product_model = ItemModel(
            entity=self,
            name=name,
            uom=uom_model,
            item_role=ItemModel.ITEM_ROLE_PRODUCT,
            item_type=item_type,
            inventory_account=account_model_qs.filter(role=roles_module.ASSET_CA_INVENTORY).get(),
            earnings_account=account_model_qs.filter(role=roles_module.INCOME_OPERATIONAL).get(),
            cogs_account=account_model_qs.filter(role=roles_module.COGS).get()
        )
        product_model.clean()
        product_model.clean_fields()
        if commit:
            product_model.save()
        return product_model

    def get_items_services(self, active: bool = True) -> ItemModelQuerySet:
        """
        Fetches all EntityModel instance ItemModel's that qualify as Services.
        QuerySet selects relevant related fields to avoid additional
        DB queries for most use cases.

        Parameters
        ----------
        active: bool
            Filters the QuerySet to active accounts only. Defaults to True.

        Returns
        -------
        ItemModelQuerySet
        """
        qs = self.get_items_all(active=active)
        return qs.services()

    def create_item_service(self,
                            name: str,
                            uom_model: Union[UUID, UnitOfMeasureModel],
                            coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                            commit: bool = True) -> ItemModel:
        """
        Creates a new items of type SERVICE.

        Parameters
        ----------
        name: str
            Name of the new service.
        uom_model:
            The UOM UUID or UnitOfMeasureModel of the Service. Will be validated if provided.
        coa_model: ChartOfAccountModel
            Optional ChartOfAccountsModel to use when fetching default role AccountModels.
        commit: bool
            Commits the ItemModel in the DB. Defaults to True.

        Returns
        -------
        ItemModel
            The created Service.
        """

        if isinstance(uom_model, UUID):
            uom_model = self.unitofmeasuremodel_set.select_related('entity').get(uuid__exact=uom_model)
        elif isinstance(uom_model, UnitOfMeasureModel):
            if uom_model.entity_id != self.uuid:
                raise EntityModelValidationError(f'Invalid UnitOfMeasureModel for entity {self.slug}...')

        account_model_qs = self.get_coa_accounts(coa_model=coa_model, active=True)
        account_model_qs = account_model_qs.with_roles(roles=[
            roles_module.COGS,
            roles_module.INCOME_OPERATIONAL
        ]).is_role_default()

        # evaluates the queryset...
        len(account_model_qs)

        service_model = ItemModel(
            entity=self,
            name=name,
            uom=uom_model,
            item_role=ItemModel.ITEM_ROLE_SERVICE,
            item_type=ItemModel.ITEM_TYPE_LABOR,
            earnings_account=account_model_qs.filter(role=roles_module.INCOME_OPERATIONAL).get(),
            cogs_account=account_model_qs.filter(role=roles_module.COGS).get()
        )
        service_model.clean()
        service_model.clean_fields()
        if commit:
            service_model.save()
        return service_model

    def get_items_expenses(self, active: bool = True) -> ItemModelQuerySet:
        """
        Fetches all EntityModel instance ItemModel's that qualify as Products.
        QuerySet selects relevant related fields to avoid additional
        DB queries for most use cases.

        Parameters
        ----------
        active: bool
            Filters the QuerySet to active accounts only. Defaults to True.

        Returns
        -------
        ItemModelQuerySet
        """
        qs = self.get_items_all(active=active)
        return qs.expenses()

    def create_item_expense(self,
                            name: str,
                            expense_type: str,
                            uom_model: Union[UUID, UnitOfMeasureModel],
                            expense_account: Optional[Union[UUID, AccountModel]] = None,
                            coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                            commit: bool = True) -> ItemModel:

        """
        Creates a new items of type EXPENSE.

        Parameters
        ----------
        name: str
            The name of the new service.
        expense_type: str
            The type of expense. A choice of ItemModel.ITEM_TYPE_CHOICES
        uom_model:
            The UOM UUID or UnitOfMeasureModel of the Service. Will be validated if provided.
        expense_account: AccountModel
            Optional EXPENSE_OPERATIONAL AccountModel associated with the new Expense Item.
            Defaults to EXPENSE_OPERATIONAL default AccountModel role.
        coa_model: ChartOfAccountModel
            Optional ChartOfAccountsModel to use when fetching default role AccountModels.
        commit: bool
            Commits the ItemModel in the DB. Defaults to True.

        Returns
        -------
        ItemModel
        """
        if isinstance(uom_model, UUID):
            uom_model = self.unitofmeasuremodel_set.select_related('entity').get(uuid__exact=uom_model)
        elif isinstance(uom_model, UnitOfMeasureModel):
            if uom_model.entity_id != self.uuid:
                raise EntityModelValidationError(f'Invalid UnitOfMeasureModel for entity {self.slug}...')

        account_model_qs = self.get_coa_accounts(coa_model=coa_model, active=True)
        account_model_qs = account_model_qs.with_roles(roles=roles_module.EXPENSE_OPERATIONAL)
        if not expense_account:
            expense_account = account_model_qs.is_role_default().get()
        elif isinstance(expense_account, UUID):
            expense_account = account_model_qs.get(uuid__exact=expense_account)
        elif isinstance(expense_account, AccountModel):
            if expense_account.coa_model.entity_id != self.uuid:
                raise EntityModelValidationError(f'Invalid account for entity {self.slug}...')

        expense_item_model = ItemModel(
            entity=self,
            name=name,
            uom=uom_model,
            item_role=ItemModel.ITEM_ROLE_EXPENSE,
            item_type=expense_type,
            expense_account=expense_account
        )
        expense_item_model.clean()
        expense_item_model.clean_fields()
        if commit:
            expense_item_model.save()
        return expense_item_model

    # ##### INVENTORY MANAGEMENT ####

    def get_items_inventory(self, active: bool = True):
        """
        Fetches all EntityModel instance ItemModel's that qualify as inventory.
        QuerySet selects relevant related fields to avoid additional
        DB queries for most use cases.

        Parameters
        ----------
        active: bool
            Filters the QuerySet to active accounts only. Defaults to True.

        Returns
        -------
        ItemModelQuerySet
        """
        qs = self.get_items_all(active=active)
        return qs.inventory_all()

    def get_items_inventory_wip(self, active: bool = True):
        """
        Fetches all EntityModel instance ItemModel's that qualify as work in progress inventory.
        QuerySet selects relevant related fields to avoid additional
        DB queries for most use cases.

        Parameters
        ----------
        active: bool
            Filters the QuerySet to active accounts only. Defaults to True.

        Returns
        -------
        ItemModelQuerySet
        """
        qs = self.get_items_all(active=active)
        return qs.inventory_wip()

    def create_item_inventory(self,
                              name: str,
                              uom_model: Union[UUID, UnitOfMeasureModel],
                              item_type: str,
                              inventory_account: Optional[Union[UUID, AccountModel]] = None,
                              coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                              commit: bool = True):
        """
        Creates a new items of type INVENTORY.

        Parameters
        ----------
        name: str
            The name of the new service.
        item_type: str
            The type of expense. A choice of ItemModel.ITEM_TYPE_CHOICES
        uom_model:
            The UOM UUID or UnitOfMeasureModel of the Service. Will be validated if provided.
        inventory_account: AccountModel
            Optional ASSET_CA_INVENTORY AccountModel associated with the new Expense Item.
            Defaults to ASSET_CA_INVENTORY default AccountModel role.
        coa_model: ChartOfAccountModel
            Optional ChartOfAccountsModel to use when fetching default role AccountModels.
        commit: bool
            Commits the ItemModel in the DB. Defaults to True.


        Returns
        -------
        ItemModel
        """
        if isinstance(uom_model, UUID):
            uom_model = self.unitofmeasuremodel_set.select_related('entity').get(uuid__exact=uom_model)
        elif isinstance(uom_model, UnitOfMeasureModel):
            if uom_model.entity_id != self.uuid:
                raise EntityModelValidationError(f'Invalid UnitOfMeasureModel for entity {self.slug}...')

        account_model_qs = self.get_coa_accounts(coa_model=coa_model, active=True)
        account_model_qs = account_model_qs.with_roles(roles=roles_module.ASSET_CA_INVENTORY)
        if not inventory_account:
            inventory_account = account_model_qs.is_role_default().get()
        elif isinstance(inventory_account, UUID):
            inventory_account = account_model_qs.get(uuid__exact=inventory_account)
        elif isinstance(inventory_account, AccountModel):
            if inventory_account.coa_model.entity_id != self.uuid:
                raise EntityModelValidationError(f'Invalid account for entity {self.slug}...')
            elif inventory_account.coa_model_id != coa_model.uuid:
                raise EntityModelValidationError(f'Invalid account for coa {coa_model.slug}...')

        inventory_item_model = ItemModel(
            name=name,
            uom=uom_model,
            entity=self,
            item_type=item_type,
            item_role=ItemModel.ITEM_ROLE_INVENTORY,
            inventory_account=inventory_account
        )
        inventory_item_model.clean()
        inventory_item_model.clean_fields()
        if commit:
            inventory_item_model.save()
        return inventory_item_model

    @staticmethod
    def inventory_adjustment(counted_qs, recorded_qs) -> defaultdict:
        """
        Computes the necessary inventory adjustment to update balance sheet.

        Parameters
        ----------
        counted_qs: ItemTransactionModelQuerySet
            Inventory recount queryset from Purchase Order received inventory.
            See :func:`ItemTransactionModelManager.inventory_count
            <django_ledger.models.item.ItemTransactionModelManager.inventory_count>`.
            Expects ItemTransactionModelQuerySet to be formatted "as values".

        recorded_qs: ItemModelQuerySet
            Inventory received currently recorded for each inventory item.
            See :func:`ItemTransactionModelManager.inventory_count
            <django_ledger.models.item.ItemTransactionModelManager.inventory_count>`
            Expects ItemModelQuerySet to be formatted "as values".

        Returns
        -------
        defaultdict
            A dictionary with necessary adjustments with keys as tuple:
                0. item_model_id
                1. item_model__name
                2. item_model__uom__name
        """
        counted_map = {
            (i['item_model_id'], i['item_model__name'], i['item_model__uom__name']): {
                'count': i['quantity_onhand'],
                'value': i['value_onhand'],
                'avg_cost': i['cost_average']
                if i['quantity_onhand'] else Decimal('0.00')
            } for i in counted_qs
        }
        recorded_map = {
            (i['uuid'], i['name'], i['uom__name']): {
                'count': i['inventory_received'] or Decimal.from_float(0.0),
                'value': i['inventory_received_value'] or Decimal.from_float(0.0),
                'avg_cost': i['inventory_received_value'] / i['inventory_received']
                if i['inventory_received'] else Decimal('0.00')
            } for i in recorded_qs
        }

        # todo: change this to use a groupby then sum...
        item_ids = list(set(list(counted_map.keys()) + list(recorded_map)))
        adjustment = defaultdict(lambda: {
            # keeps track of inventory recounts...
            'counted': Decimal('0.000'),
            'counted_value': Decimal('0.00'),
            'counted_avg_cost': Decimal('0.00'),

            # keeps track of inventory level...
            'recorded': Decimal('0.000'),
            'recorded_value': Decimal('0.00'),
            'recorded_avg_cost': Decimal('0.00'),

            # keeps track of necessary inventory adjustment...
            'count_diff': Decimal('0.000'),
            'value_diff': Decimal('0.00'),
            'avg_cost_diff': Decimal('0.00')
        })

        for uid in item_ids:

            count_data = counted_map.get(uid)
            if count_data:
                avg_cost = count_data['value'] / count_data['count'] if count_data['count'] else Decimal('0.000')

                adjustment[uid]['counted'] = count_data['count']
                adjustment[uid]['counted_value'] = count_data['value']
                adjustment[uid]['counted_avg_cost'] = avg_cost

                adjustment[uid]['count_diff'] += count_data['count']
                adjustment[uid]['value_diff'] += count_data['value']
                adjustment[uid]['avg_cost_diff'] += avg_cost

            recorded_data = recorded_map.get(uid)
            if recorded_data:
                counted = recorded_data['count']
                avg_cost = recorded_data['value'] / counted if recorded_data['count'] else Decimal('0.000')

                adjustment[uid]['recorded'] = counted
                adjustment[uid]['recorded_value'] = recorded_data['value']
                adjustment[uid]['recorded_avg_cost'] = avg_cost

                adjustment[uid]['count_diff'] -= counted
                adjustment[uid]['value_diff'] -= recorded_data['value']
                adjustment[uid]['avg_cost_diff'] -= avg_cost
        return adjustment

    def update_inventory(self,
                         commit: bool = False) -> Tuple[defaultdict, ItemTransactionModelQuerySet, ItemModelQuerySet]:
        """
        Triggers an inventory recount with optional commitment of transaction.

        Parameters
        ----------
        commit:
            Updates all inventory ItemModels with the new inventory count.

        Returns
        -------
        Tuple[defaultdict, ItemTransactionModelQuerySet, ItemModelQuerySet]
            Return a tuple as follows:
                0. All necessary inventory adjustments as a dictionary.
                1. The recounted inventory.
                2. The recorded inventory on Balance Sheet.
        """
        ItemTransactionModel = lazy_loader.get_item_transaction_model()
        ItemModel = lazy_loader.get_item_model()

        counted_qs: ItemTransactionModelQuerySet = ItemTransactionModel.objects.inventory_count(entity_slug=self.slug)
        recorded_qs: ItemModelQuerySet = self.recorded_inventory(as_values=False)
        recorded_qs_values = self.recorded_inventory(item_qs=recorded_qs, as_values=True)

        adj = self.inventory_adjustment(counted_qs, recorded_qs_values)

        updated_items = list()
        for (uuid, name, uom), i in adj.items():
            item_model: ItemModel = recorded_qs.get(uuid__exact=uuid)
            item_model.inventory_received = i['counted']
            item_model.inventory_received_value = i['counted_value']
            item_model.clean()
            updated_items.append(item_model)

        if commit:
            ItemModel.objects.bulk_update(updated_items,
                                          fields=[
                                              'inventory_received',
                                              'inventory_received_value',
                                              'updated'
                                          ])

        return adj, counted_qs, recorded_qs

    def recorded_inventory(self,
                           item_qs: Optional[ItemModelQuerySet] = None,
                           as_values: bool = True) -> ItemModelQuerySet:
        """
        Recorded inventory on the books marked as received. PurchaseOrderModel drives the ordering and receiving of
        inventory. Once inventory is marked as "received" recorded inventory of each item is updated by calling
        :func:`update_inventory <django_ledger.models.entity.EntityModelAbstract.update_inventory>`.
        This function returns relevant values of the recoded inventory, including Unit of Measures.

        Parameters
        ----------
        item_qs: ItemModelQuerySet
            Pre fetched ItemModelQuerySet. Avoids additional DB Query.

        as_values: bool
            Returns a list of dictionaries by calling the Django values() QuerySet function.


        Returns
        -------
        ItemModelQuerySet
            The ItemModelQuerySet containing inventory ItemModels with additional Unit of Measure information.

        """
        if not item_qs:
            recorded_qs = self.itemmodel_set.all().inventory_all()
        else:
            self.validate_item_qs(item_qs)
            recorded_qs = item_qs
        if as_values:
            return recorded_qs.values(
                'uuid', 'name', 'uom__name', 'inventory_received', 'inventory_received_value')
        return recorded_qs

    # COMMON TRANSACTIONS...
    def deposit_capital(self,
                        amount: Union[Decimal, float],
                        cash_account: Optional[Union[AccountModel, BankAccountModel]] = None,
                        capital_account: Optional[AccountModel] = None,
                        description: Optional[str] = None,
                        coa_model: Optional[Union[ChartOfAccountModel, UUID, str]] = None,
                        ledger_model: Optional[Union[LedgerModel, UUID]] = None,
                        ledger_posted: bool = False,
                        je_timestamp: Optional[Union[datetime, date, str]] = None,
                        je_posted: bool = False):

        if coa_model:
            self.validate_chart_of_accounts_for_entity(coa_model)
        else:
            coa_model = self.get_default_coa()

        ROLES_NEEDED = list()
        if not cash_account:
            ROLES_NEEDED.append(roles_module.ASSET_CA_CASH)

        if not capital_account:
            ROLES_NEEDED.append(roles_module.EQUITY_CAPITAL)

        account_model_qs = self.get_coa_accounts(coa_model=coa_model)
        account_model_qs = account_model_qs.with_roles(roles=ROLES_NEEDED).is_role_default()

        if not cash_account or not capital_account:
            if cash_account or capital_account:
                len(account_model_qs)

        if cash_account:
            if isinstance(cash_account, BankAccountModel):
                cash_account = cash_account.cash_account
            self.validate_account_model_for_coa(account_model=cash_account, coa_model=coa_model)
            self.validate_account_model_for_role(cash_account, roles_module.ASSET_CA_CASH)
        else:
            cash_account = account_model_qs.filter(role__exact=roles_module.ASSET_CA_CASH).get()

        if capital_account:
            self.validate_account_model_for_coa(account_model=capital_account, coa_model=coa_model)
            self.validate_account_model_for_role(capital_account, roles_module.EQUITY_CAPITAL)
        else:
            capital_account = account_model_qs.filter(role__exact=roles_module.EQUITY_CAPITAL).get()

        if not je_timestamp:
            je_timestamp = localtime()

        if not description:
            description = f'Capital Deposit on {je_timestamp.isoformat()}...'

        txs = list()
        txs.append({
            'account': cash_account,
            'tx_type': DEBIT,
            'amount': amount,
            'description': description
        })
        txs.append({
            'account': capital_account,
            'tx_type': CREDIT,
            'amount': amount,
            'description': description
        })

        if not ledger_model:
            ledger_model = self.ledgermodel_set.create(
                name=f'Capital Deposit on {je_timestamp.isoformat()}.',
                posted=ledger_posted
            )
        else:
            if isinstance(ledger_model, LedgerModel):
                self.validate_ledger_model_for_entity(ledger_model)
            else:
                ledger_model_qs = LedgerModel.objects.filter(entity__uuid__exact=self.uuid)
                ledger_model = ledger_model_qs.get(uuid__exact=ledger_model)

        self.commit_txs(
            je_timestamp=je_timestamp,
            je_txs=txs,
            je_posted=je_posted,
            je_ledger_model=ledger_model
        )

        return ledger_model

    # ### CLOSING DATA ###

    def has_closing_entry(self):
        return self.last_closing_date is not None

    # ### RANDOM DATA GENERATION ####

    def populate_random_data(self, start_date: date, days_forward=180):
        EntityDataGenerator = lazy_loader.get_entity_data_generator()
        data_generator = EntityDataGenerator(
            user_model=self.admin,
            days_forward=days_forward,
            start_date=start_date,
            entity_model=self,
            capital_contribution=Decimal.from_float(50000.00)
        )
        data_generator.populate_entity()

    # URLS ----
    def get_dashboard_url(self) -> str:
        """
        The EntityModel Dashboard URL.

        Returns
        _______
        str
            EntityModel dashboard URL as a string.
        """
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_manage_url(self) -> str:
        """
        The EntityModel Manage URL.

        Returns
        _______
        str
            EntityModel manage URL as a string.
        """
        return reverse('django_ledger:entity-update',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_ledgers_url(self) -> str:
        """
        The EntityModel Ledger List URL.

        Returns
        _______
        str
            EntityModel ledger list URL as a string.
        """
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_bills_url(self) -> str:
        """
        The EntityModel bill list URL.

        Returns
        _______
        str
            EntityModel bill list URL as a string.
        """
        return reverse('django_ledger:bill-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_invoices_url(self) -> str:
        """
        The EntityModel invoice list URL.

        Returns
        _______
        str
            EntityModel invoice list URL as a string.
        """
        return reverse('django_ledger:invoice-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_banks_url(self) -> str:
        """
        The EntityModel bank account list URL.

        Returns
        _______
        str
            EntityModel bank account list URL as a string.
        """
        return reverse('django_ledger:bank-account-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_balance_sheet_url(self) -> str:
        """
        The EntityModel Balance Sheet Statement URL.

        Returns
        _______
        str
            EntityModel Balance Sheet Statement URL as a string.
        """
        return reverse('django_ledger:entity-bs',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_income_statement_url(self) -> str:
        """
        The EntityModel Income Statement URL.

        Returns
        _______
        str
            EntityModel Income Statement URL as a string.
        """
        return reverse('django_ledger:entity-ic',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_cashflow_statement_url(self) -> str:
        """
        The EntityModel Cashflow Statement URL.

        Returns
        _______
        str
            EntityModel Cashflow Statement URL as a string.
        """
        return reverse('django_ledger:entity-cf',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_data_import_url(self) -> str:
        """
        The EntityModel transaction import URL.

        Returns
        _______
        str
            EntityModel transaction import URL as a string.
        """
        return reverse('django_ledger:data-import-jobs-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_accounts_url(self) -> str:
        """
        The EntityModel Code of Accounts llist import URL.

        Returns
        _______
        str
            EntityModel Code of Accounts llist import URL as a string.
        """
        return reverse('django_ledger:account-list',
                       kwargs={
                           'entity_slug': self.slug,
                       })

    def get_customers_url(self) -> str:
        """
        The EntityModel customers list URL.

        Returns
        _______
        str
            EntityModel customers list URL as a string.
        """
        return reverse('django_ledger:customer-list',
                       kwargs={
                           'entity_slug': self.slug,
                       })

    def get_vendors_url(self) -> str:
        """
        The EntityModel vendors list URL.

        Returns
        _______
        str
            EntityModel vendors list URL as a string.
        """
        return reverse('django_ledger:vendor-list',
                       kwargs={
                           'entity_slug': self.slug,
                       })

    def get_delete_url(self) -> str:
        """
        The EntityModel delete URL.

        Returns
        _______
        str
            EntityModel delete URL as a string.
        """
        return reverse('django_ledger:entity-delete',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def clean(self):
        if not self.slug:
            self.generate_slug()
        super(EntityModelAbstract, self).clean()


class EntityModel(EntityModelAbstract):
    """
    Entity Model Base Class From Abstract
    """


# ## ENTITY STATE....
class EntityStateModelAbstract(models.Model):
    KEY_JOURNAL_ENTRY = 'je'
    KEY_PURCHASE_ORDER = 'po'
    KEY_BILL = 'bill'
    KEY_INVOICE = 'invoice'
    KEY_ESTIMATE = 'estimate'
    KEY_VENDOR = 'vendor'
    KEY_CUSTOMER = 'customer'
    KEY_ITEM = 'item'

    KEY_CHOICES = [
        (KEY_JOURNAL_ENTRY, _('Journal Entry')),
        (KEY_PURCHASE_ORDER, _('Purchase Order')),
        (KEY_BILL, _('Bill')),
        (KEY_INVOICE, _('Invoice')),
        (KEY_ESTIMATE, _('Estimate')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity_model = models.ForeignKey('django_ledger.EntityModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_('Entity Model'))
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel',
                                    on_delete=models.RESTRICT,
                                    verbose_name=_('Entity Unit'),
                                    blank=True,
                                    null=True)
    fiscal_year = models.SmallIntegerField(
        verbose_name=_('Fiscal Year'),
        validators=[MinValueValidator(limit_value=1900)],
        null=True,
        blank=True
    )
    key = models.CharField(choices=KEY_CHOICES, max_length=10)
    sequence = models.BigIntegerField(default=0, validators=[MinValueValidator(limit_value=0)])

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['key']),
            models.Index(
                fields=[
                    'entity_model',
                    'fiscal_year',
                    'entity_unit',
                    'key'
                ])
        ]
        unique_together = [
            ('entity_model', 'entity_unit', 'fiscal_year', 'key')
        ]

    def __str__(self):
        return f'{self.__class__.__name__} {self.entity_id}: FY: {self.fiscal_year}, KEY: {self.get_key_display()}'


class EntityStateModel(EntityStateModelAbstract):
    """
    Entity State Model Base Class from Abstract.
    """


# ## ENTITY MANAGEMENT.....
class EntityManagementModelAbstract(CreateUpdateMixIn):
    """
    Entity Management Model responsible for manager permissions to read/write.
    """
    PERMISSIONS = [
        ('read', _('Read Permissions')),
        ('write', _('Read/Write Permissions')),
        ('suspended', _('No Permissions'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Entity'),
                               related_name='entity_permissions')
    user = models.ForeignKey(UserModel,
                             on_delete=models.CASCADE,
                             verbose_name=_('Manager'),
                             related_name='entity_permissions')
    permission_level = models.CharField(max_length=10,
                                        default='read',
                                        choices=PERMISSIONS,
                                        verbose_name=_('Permission Level'))

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['entity', 'user']),
            models.Index(fields=['user', 'entity'])
        ]


class EntityManagementModel(EntityManagementModelAbstract):
    """
    EntityManagement Model Base Class From Abstract
    """


def entitymodel_presave(instance: EntityModel, **kwargs):
    if not instance.slug:
        instance.generate_slug(commit=False)


pre_save.connect(receiver=entitymodel_presave, sender=EntityModel)
