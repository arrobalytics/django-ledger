"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

An EntityUnit is a logical, user-defined grouping which is assigned to JournalEntryModels to help segregate business
operations into separate components. Examples of business units may include Departments (i.e. Human Resources, IT, etc.)
office locations, a real estate property, or any other label relevant to the business.

An EntityUnit is self contained. Meaning that double entry accounting rules apply to all transactions associated within
them. When An Invoice or Bill is updated, the migration process generates the appropriate Journal Entries associated
with each unit, if any. This means that an invoice or bill can split items into different units and the migration
process will allocate costs to each unit accordingly.

The main advantages of EntityUnits are:
    1. Entity units can generate their own financial statements which can give additional insight to specific operations
       of the business.
    2. Entity units can be assigned to specific items on Bills and Invoices, providing additional flexibility to track
       inventory, expenses or income attributable to specific units of the business.
"""

from random import choices
from string import ascii_lowercase, digits, ascii_uppercase
from typing import Optional
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from treebeard.mp_tree import MP_Node, MP_NodeManager, MP_NodeQuerySet

from django_ledger.io.io_core import IOMixIn
from django_ledger.models import lazy_loader
from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn

ENTITY_UNIT_RANDOM_SLUG_SUFFIX = ascii_lowercase + digits


class EntityUnitModelValidationError(ValidationError):
    pass


class EntityUnitModelQuerySet(MP_NodeQuerySet):
    """
    A custom defined EntityUnitModel Queryset.
    """


class EntityUnitModelManager(MP_NodeManager):

    def for_user(self, user_model):
        qs = self.get_queryset()
        if user_model.is_superuser:
            return qs
        return qs.filter(
            Q(entity__admin=user_model) |
            Q(entity__managers__in=[user_model])
        )

    def for_entity(self, entity_slug: str, user_model):
        """
        Fetches a QuerySet of EntityUnitModels associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        ----------
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model
            Logged in and authenticated django UserModel instance.

        Examples
        --------
            >>> request_user = request.user
            >>> slug = kwargs['entity_slug'] # may come from request kwargs
            >>> bill_model_qs = EntityUnitModel.objects.for_entity(user_model=request_user, entity_slug=slug)

        Returns
        -------
        EntityUnitModelQuerySet
            Returns a EntityUnitModelQuerySet with applied filters.
        """
        qs = self.for_user(user_model)
        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return qs.filter(
                Q(entity=entity_slug)

            )
        return qs.filter(
            Q(entity__slug__exact=entity_slug)
        )


class EntityUnitModelAbstract(MP_Node,
                              IOMixIn,
                              SlugNameMixIn,
                              CreateUpdateMixIn):
    """
    Base implementation of the EntityUnitModel.

    Attributes
    ----------
    uuid : UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().

    slug: str
        A unique, indexed identifier for the EntityUnitModel instance used in URLs and queries.

    entity: EntityModel
        The EntityModel associated with this EntityUnitModel.

    document_prefix: str
        A predefined prefix automatically incorporated into JournalEntryModel document numbers. Max Length 3.
        May be user defined. Must be unique for the EntityModel.

    active: bool
        Active EntityUnits may transact. Inactive units are considered archived. Defaults to True.

    hidden: bool
        Hidden Units will not show on drop down menus on the UI. Defaults to False.
    """
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    slug = models.SlugField(max_length=50)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('Unit Entity'))
    document_prefix = models.CharField(max_length=3)
    active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    hidden = models.BooleanField(default=False, verbose_name=_('Is Hidden'))

    objects = EntityUnitModelManager.from_queryset(queryset_class=EntityUnitModelQuerySet)()
    node_order_by = ['uuid']

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Entity Unit Model')
        unique_together = [
            ('entity', 'slug'),
            ('entity', 'document_prefix'),
        ]
        indexes = [
            models.Index(fields=['active']),
            models.Index(fields=['hidden']),
            models.Index(fields=['entity']),
        ]

    def __str__(self):
        return f'Unit: {self.name}'

    def clean(self):
        self.create_entity_unit_slug()

        if not self.document_prefix:
            self.document_prefix = ''.join(choices(ascii_uppercase, k=3))

    def get_dashboard_url(self) -> str:
        """
        The dashboard URL of the EntityModelUnit.

        Returns
        -------
        str
            The EntityModelUnit instance dashboard URL.
        """
        return reverse('django_ledger:unit-dashboard',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_entity_name(self) -> str:
        return self.entity.name

    def create_entity_unit_slug(self,
                                name: Optional[str] = None,
                                force: bool = False,
                                add_suffix: bool = True,
                                k: int = 5) -> str:
        """
        Automatically generates a EntityUnitModel slug. If slug is present, will not be replaced.
        Called during the clean() method.

        Parameters
        ----------
        force: bool
            Forces generation of new slug if already present.
        name: str
            The name used to create slug. If none, the unit name will be used.
        add_suffix: bool
            Adds a random suffix to the slug. Defaults to True.
        k: int
            Length of the suffix if add_suffix is True. Defaults to 5.

        Returns
        -------
        str
            The EntityUnitModel slug, regardless if generated or not.
        """
        if not self.slug or force:
            if not name:
                name = f'{self.name} Unit'
            unit_slug = slugify(name)
            if add_suffix:
                suffix = ''.join(choices(ENTITY_UNIT_RANDOM_SLUG_SUFFIX, k=k))
                unit_slug = f'{unit_slug}-{suffix}'
            self.slug = unit_slug
        return self.slug

    def get_absolute_url(self):
        return reverse(
            viewname='django_ledger:unit-detail',
            kwargs={
                'entity_slug': self.entity.slug,
                'unit_slug': self.slug
            }
        )


class EntityUnitModel(EntityUnitModelAbstract):
    """
    Base Model Class for EntityUnitModel
    """
