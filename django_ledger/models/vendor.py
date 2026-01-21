"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

A Vendor refers to the person or entity that provides products and services to the business for a fee.
Vendors are an integral part of the billing process as they are the providers of goods and services for the
business.

Vendors can be flagged as active/inactive or hidden. Vendors who no longer conduct business with the EntityModel,
whether temporarily or indefinitely may be flagged as inactive (i.e. active is False). Hidden Vendors will not show up
as an option in the UI, but can still be used programmatically (via API).
"""

import os
import warnings
from uuid import UUID, uuid4

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import F, Manager, Q, QuerySet
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from django_ledger.models.deprecations import deprecated_entity_slug_behavior
from django_ledger.models.mixins import (
    ContactInfoMixIn,
    CreateUpdateMixIn,
    FinancialAccountInfoMixin,
    TaxInfoMixIn,
)
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import (
    DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
    DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR,
    DJANGO_LEDGER_VENDOR_NUMBER_PREFIX,
)


def vendor_picture_upload_to(instance, filename):
    if not instance.customer_number:
        instance.generate_customer_number(commit=False)
    vendor_number = instance.customer_number
    name, ext = os.path.splitext(filename)
    safe_name = slugify(name)
    return f'vendor_pictures/{vendor_number}/{safe_name}{ext.lower()}'


class VendorModelValidationError(ValidationError):
    pass


class VendorModelQuerySet(QuerySet):
    """
    Custom defined VendorModel QuerySet.
    """

    def for_user(self, user_model) -> 'VendorModelQuerySet':
        if user_model.is_superuser:
            return self
        return self.filter(
            Q(entity_model__admin=user_model)
            | Q(entity_model__managers__in=[user_model])
        )

    def active(self) -> 'VendorModelQuerySet':
        """
        Active vendors can be assigned to new bills and show on dropdown menus and views.

        Returns
        -------
        VendorModelQuerySet
            A QuerySet of active Vendors.
        """
        return self.filter(active=True)

    def inactive(self) -> 'VendorModelQuerySet':
        """
        Active vendors can be assigned to new bills and show on dropdown menus and views.
        Marking VendorModels as inactive can help reduce Database load to populate select inputs and also inactivate
        VendorModels that are not relevant to the Entity anymore. Also, it makes de UI cleaner by not populating
        unnecessary choices.

        Returns
        -------
        VendorModelQuerySet
            A QuerySet of inactive Vendors.
        """
        return self.filter(active=False)

    def hidden(self) -> 'VendorModelQuerySet':
        """
        Hidden vendors do not show on dropdown menus, but may be used via APIs or any other method that does not
        involve the UI.

        Returns
        -------
        VendorModelQuerySet
            A QuerySet of hidden Vendors.
        """
        return self.filter(hidden=True)

    def visible(self) -> 'VendorModelQuerySet':
        """
        Visible vendors show on dropdown menus and views. Visible vendors are active and not hidden.

        Returns
        -------
        VendorModelQuerySet
            A QuerySet of visible Vendors.
        """
        return self.filter(Q(hidden=False) & Q(active=True))


class VendorModelManager(Manager):
    """
    Manages operations related to VendorModel instances.

    A specialized manager for handling interactions with VendorModel entities,
    providing additional support for filtering based on associated EntityModel or EntityModel slug.
    """

    def get_queryset(self) -> VendorModelQuerySet:
        qs = VendorModelQuerySet(self.model, using=self._db)
        return qs.select_related(
            'entity_model'
        ).annotate(
            _entity_slug=F('entity_model__slug'),
        )

    @deprecated_entity_slug_behavior
    def for_entity(
            self, entity_model: 'EntityModel | str | UUID' = None, **kwargs
    ) -> VendorModelQuerySet:
        """
        Filters the queryset for a given entity model.

        This method modifies the queryset to include only those records
        associated with the specified entity model. The entity model can
        be provided in various formats, such as an instance of `EntityModel`,
        a string representing the entity's slug, or its UUID.

        If a deprecated parameter `user_model` is provided, it will issue
        a warning and may alter the behavior if the deprecated behavior flag
        `DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR` is set.

        Parameters
        ----------
        entity_model : EntityModel | str | UUID
            The entity model or its identifier (slug or UUID) to filter the
            queryset by.

        **kwargs
            Additional parameters for optional functionality. The parameter
            `user_model` is supported for backward compatibility but is
            deprecated and should be avoided.

        Returns
        -------
        VendorModelQuerySet
            A queryset filtered for the given entity model.
        """
        EntityModel = lazy_loader.get_entity_model()

        qs = self.get_queryset()
        if 'user_model' in kwargs:
            warnings.warn(
                'user_model parameter is deprecated and will be removed in a future release. '
                'Use for_user(user_model).for_entity(entity_model) instead to keep current behavior.',
                DeprecationWarning,
                stacklevel=2,
            )

            if DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR:
                qs = qs.for_user(kwargs['user_model'])

        if isinstance(entity_model, EntityModel):
            qs = qs.filter(entity_model=entity_model)
        elif isinstance(entity_model, str):
            qs = qs.filter(entity_model__slug__exact=entity_model)
        elif isinstance(entity_model, UUID):
            qs = qs.filter(entity_model_id=entity_model)
        else:
            raise VendorModelValidationError(
                'EntityModel slug must be either a string or an EntityModel instance'
            )
        return qs


class VendorModelAbstract(
    ContactInfoMixIn, FinancialAccountInfoMixin, TaxInfoMixIn, CreateUpdateMixIn
):
    """
    This is the main abstract class which the VendorModel database will inherit from.
    The VendorModel inherits functionality from the following MixIns:

        1. :func:`ContactInfoMixIn <django_ledger.models.mixins.ContactInfoMixIn>`
        2. :func:`BankAccountInfoMixIn <django_ledger.models.mixins.BankAccountInfoMixIn>`
        3. :func:`TaxInfoMixIn <django_ledger.models.mixins.TaxInfoMixIn>`
        4. :func:`CreateUpdateMixIn <django_ledger.models.mixins.CreateUpdateMixIn>`

    Attributes
    __________

    uuid : UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().

    entity_model: EntityModel
        The EntityModel associated with this Vendor.

    vendor_name: str
        A string representing the name the customer uses to do business with the EntityModel.

    vendor_number: str
        A unique, auto-generated human-readable number which identifies the vendor within the EntityModel.

    description: str
        A text field to capture the description about the vendor.

    active: bool
        We can set any vendor to be active or inactive. Defaults to True.

    hidden: bool
        Hidden VendorModel don't show on the UI. Defaults to False.

    additional_info: dict
        Any additional information about the vendor, stored as a JSON object using a JSONField.


    """

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    vendor_code = models.SlugField(
        max_length=50, null=True, blank=True, verbose_name='User defined vendor code.'
    )
    vendor_number = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_('Vendor Number'),
        help_text='System generated vendor number.',
    )
    vendor_name = models.CharField(max_length=100)

    entity_model = models.ForeignKey(
        'django_ledger.EntityModel',
        on_delete=models.CASCADE,
        verbose_name=_('Vendor Entity'),
        editable=False,
    )
    description = models.TextField()
    active = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)
    picture = models.ImageField(
        upload_to=vendor_picture_upload_to, null=True, blank=True
    )

    additional_info = models.JSONField(null=True, blank=True, default=dict)

    objects = VendorModelManager.from_queryset(queryset_class=VendorModelQuerySet)()

    class Meta:
        verbose_name = _('Vendor')
        indexes = [
            models.Index(fields=['entity_model', 'vendor_number']),
            models.Index(fields=['vendor_number']),
            models.Index(fields=['created']),
            models.Index(fields=['updated']),
            models.Index(fields=['active']),
            models.Index(fields=['hidden']),
        ]
        unique_together = [('entity_model', 'vendor_number')]
        abstract = True

    def __str__(self):
        if not self.vendor_number:
            f'Unknown Vendor: {self.vendor_name}'
        return f'{self.vendor_number}: {self.vendor_name}'

    @property
    def entity_slug(self) -> str:
        try:
            return getattr(self, '_entity_slug')
        except AttributeError:
            return self.entity_model.slug

    def validate_for_entity(self, entity_model: 'EntityModel | str | UUID'):
        EntityModel = lazy_loader.get_entity_model()
        if isinstance(entity_model, str):
            is_valid = entity_model == self.entity_model.slug
        elif isinstance(entity_model, EntityModel):
            is_valid = entity_model == self.entity_model
        elif isinstance(entity_model, UUID):
            is_valid = entity_model == self.entity_model_id

        if not is_valid:
            raise VendorModelValidationError(
                'EntityModel does not belong to this Vendor'
            )

    def can_generate_vendor_number(self) -> bool:
        """
        Determines if the VendorModel can be issued a Vendor Number.
        VendorModel have a unique sequential number, which is unique for each EntityModel/VendorModel.

        Returns
        -------
        bool
            True if the vendor number can be generated, else False.
        """
        return all([self.entity_model_id, not self.vendor_number])

    def _get_next_state_model(self, raise_exception: bool = True):
        """
        Fetches the updated EntityStateModel associated with the vendor number sequence.
        If EntityStateModel is not present, a new model will be created.

        Parameters
        ----------
        raise_exception: bool
            Raises IntegrityError if Database cannot determine the next EntityStateModel available.

        Returns
        -------
        EntityStateModel
            The EntityStateModel associated with the VendorModel number sequence.
        """
        EntityStateModel = lazy_loader.get_entity_state_model()

        try:
            LOOKUP = {
                'entity_model_id__exact': self.entity_model_id,
                'key__exact': EntityStateModel.KEY_VENDOR,
            }

            state_model_qs = EntityStateModel.objects.filter(
                **LOOKUP
            ).select_for_update()
            state_model = state_model_qs.get()
            state_model.sequence = F('sequence') + 1
            state_model.save()
            state_model.refresh_from_db()

            return state_model
        except ObjectDoesNotExist:
            LOOKUP = {
                'entity_model_id': self.entity_model_id,
                'entity_unit_id': None,
                'fiscal_year': None,
                'key': EntityStateModel.KEY_VENDOR,
                'sequence': 1,
            }
            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model
        except IntegrityError as e:
            if raise_exception:
                raise e

    def generate_vendor_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next Vendor Number available.

        Parameters
        __________

        commit: bool
            Commits transaction into VendorModel. Defaults to False.

        Returns
        _______
        str
            A String, representing the current VendorModel instance document number.
        """
        if self.can_generate_vendor_number():
            with transaction.atomic(durable=True):
                state_model = None
                while not state_model:
                    state_model = self._get_next_state_model(raise_exception=False)

            seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
            self.vendor_number = f'{DJANGO_LEDGER_VENDOR_NUMBER_PREFIX}-{seq}'

            if commit:
                self.save(update_fields=['vendor_number', 'updated'])

        return self.vendor_number

    def get_absolute_url(self):
        return reverse('django_ledger:vendor-detail',
                       kwargs={
                           'entity_slug': self.entity_slug,
                           'vendor_pk': self.uuid
                       })

    def get_detail_url(self):
        return self.get_absolute_url()

    def get_update_url(self):
        return reverse('django_ledger:vendor-update',
                       kwargs={
                           'entity_slug': self.entity_slug,
                           'vendor_pk': self.uuid
                       })

    def clean(self):
        """
        Custom defined clean method that fetches the next vendor number if not yet fetched.
        Additional validation may be provided.
        """
        if self.can_generate_vendor_number():
            self.generate_vendor_number(commit=False)

    def save(self, **kwargs):
        """
        Custom-defined save method that automatically fetches the vendor number if not present.

        Parameters
        ----------
        kwargs
            Keywords passed to the super().save() method of the VendorModel.
        """
        if self.can_generate_vendor_number():
            self.generate_vendor_number(commit=False)
        super(VendorModelAbstract, self).save(**kwargs)


class VendorModel(VendorModelAbstract):
    """
    Base Vendor Model Implementation
    """

    class Meta(VendorModelAbstract.Meta):
        abstract = False
