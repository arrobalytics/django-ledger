"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

A Customer refers to the person or entity that buys product and services. When issuing Invoices, a Customer must be
created before it can be assigned to the InvoiceModel. Only customers who are active can be assigned to new Invoices.
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
    TaxCollectionMixIn,
)
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import (
    DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX,
    DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
    DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR,
)


def customer_picture_upload_to(instance, filename):
    """
    Stores pictures under: customer_pictures/<customer_number>/<sanitized-filename>.<ext>
    """
    if not instance.customer_number:
        instance.generate_customer_number(commit=False)
    customer_number = instance.customer_number
    name, ext = os.path.splitext(filename)
    safe_name = slugify(name)
    return f'customer_pictures/{customer_number}/{safe_name}{ext.lower()}'


class CustomerModelValidationError(ValidationError):
    pass


class CustomerModelQueryset(QuerySet):
    """
    A custom defined QuerySet for the CustomerModel. This implements multiple methods or queries needed to get a
    filtered QuerySet based on the CustomerModel status. For example, we might want to have list of Customers that
    are active or hidden. All these separate functions will assist in making such queries and building customized
    reports.
    """

    def for_user(self, user_model) -> 'CustomerModelQueryset':
        """
        Fetches a QuerySet of BillModels that the UserModel as access to.
        May include BillModels from multiple Entities.

        The user has access to bills if:
            1. Is listed as Manager of Entity.
            2. Is the Admin of the Entity.

        Parameters
        __________
        user_model
            Logged in and authenticated django UserModel instance.
        """
        if user_model.is_superuser:
            return self
        return self.filter(Q(entity_model__admin=user_model) | Q(entity_model__managers__in=[user_model]))

    def active(self) -> 'CustomerModelQueryset':
        """
        Active customers can be assigned to new Invoices and show on dropdown menus and views.

        Returns
        -------
        CustomerModelQueryset
            A QuerySet of active Customers.
        """
        return self.filter(active=True)

    def inactive(self) -> 'CustomerModelQueryset':
        """
        Active customers can be assigned to new Invoices and show on dropdown menus and views.
        Marking CustomerModels as inactive can help reduce Database load to populate select inputs and also inactivate
        CustomerModels that are not relevant to the Entity anymore. Also, it makes de UI cleaner by not populating
        unnecessary choices.

        Returns
        -------
        CustomerModelQueryset
            A QuerySet of inactive Customers.
        """
        return self.filter(active=False)

    def hidden(self) -> 'CustomerModelQueryset':
        """
        Hidden customers do not show on dropdown menus, but may be used via APIs or any other method that does not
        involve the UI.

        Returns
        -------
        CustomerModelQueryset
            A QuerySet of hidden Customers.
        """
        return self.filter(hidden=True)

    def visible(self) -> 'CustomerModelQueryset':
        """
        Visible customers show on dropdown menus and views. Visible customers are active and not hidden.

        Returns
        -------
        CustomerModelQueryset
            A QuerySet of visible Customers.
        """
        return self.filter(Q(hidden=False) & Q(active=True))


class CustomerModelManager(Manager):
    """
    A custom-defined CustomerModelManager that will act as an interface to handling the DB queries to the
    CustomerModel.
    """

    def get_queryset(self) -> CustomerModelQueryset:
        qs = CustomerModelQueryset(self.model, using=self._db)
        return qs.select_related('entity_model').annotate(
            _entity_slug=F('entity_model__slug')
        )

    @deprecated_entity_slug_behavior
    def for_entity(self, entity_model: 'EntityModel | str | UUID', **kwargs) -> CustomerModelQueryset:  # noqa: F821
        """
        Fetches a QuerySet of CustomerModel associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        __________
        entity_model: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.

        Returns
        -------
        CustomerModelQueryset
            A filtered CustomerModel QuerySet.
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
            return qs.filter(entity_model=entity_model)
        elif isinstance(entity_model, str):
            return qs.filter(entity_model__slug__exact=entity_model)
        elif isinstance(entity_model, UUID):
            return qs.filter(entity_model_id=entity_model)
        else:
            raise CustomerModelValidationError(
                message='Must pass EntityModel, slug or EntityModel UUID',
            )


class CustomerModelAbstract(ContactInfoMixIn, TaxCollectionMixIn, CreateUpdateMixIn):
    """
    This is the main abstract class which the CustomerModel database will inherit from.
    The CustomerModel inherits functionality from the following MixIns:

        1. :func:`ContactInfoMixIn <django_ledger.models.mixins.ContactInfoMixIn>`
        2. :func:`CreateUpdateMixIn <django_ledger.models.mixins.CreateUpdateMixIn>`

    Attributes
    __________
    uuid : UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().

    entity_model: EntityModel
        The EntityModel associated with this Customer.

    customer_name: str
        A string representing the name the customer uses to do business with the EntityModel.

    customer_number: str
        A unique, auto-generated human-readable number which identifies the customer within the EntityModel.

    description: str
        A text field to capture the description about the customer.

    active: bool
        We can set any customer code to be active or inactive. Defaults to True.

    hidden: bool
        Hidden CustomerModels don't show on the UI. Defaults to False.

    additional_info: dict
        Any additional information about the customer, stored as a JSON object using a JSONField.
    """

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    customer_code = models.SlugField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name='User defined customer code',
    )
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(
        max_length=30,
        editable=False,
        verbose_name=_('Customer Number'),
        help_text='System generated customer number.',
    )
    entity_model = models.ForeignKey(
        'django_ledger.EntityModel',
        editable=False,
        on_delete=models.CASCADE,
        verbose_name=_('Customer Entity'),
    )
    description = models.TextField()
    active = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)
    picture = models.ImageField(upload_to=customer_picture_upload_to, null=True, blank=True)

    additional_info = models.JSONField(null=True, blank=True, default=dict)

    objects = CustomerModelManager.from_queryset(queryset_class=CustomerModelQueryset)()

    class Meta:
        abstract = True
        verbose_name = _('Customer')
        indexes = [
            models.Index(fields=['entity_model', 'customer_number']),
            models.Index(fields=['created']),
            models.Index(fields=['updated']),
            models.Index(fields=['active']),
            models.Index(fields=['hidden']),
        ]
        unique_together = [('entity_model', 'customer_number')]

    def __str__(self):
        if not self.customer_number:
            f'Unknown Customer: {self.customer_name}'
        return f'{self.customer_number}: {self.customer_name}'

    @property
    def entity_slug(self) -> str:
        try:
            return getattr(self, '_entity_slug')
        except AttributeError:
            pass
        return self.entity_model.slug

    def can_generate_customer_number(self) -> bool:
        """
        Determines if the CustomerModel can be issued a Customer Number.
        CustomerModels have a unique sequential number, which is unique for each EntityMode/CustomerModel.

        Returns
        -------
        bool
            True if customer model can be generated, else False.
        """
        return all([self.entity_model_id, not self.customer_number])

    def _get_next_state_model(self, raise_exception: bool = True):
        """
        Fetches the updated EntityStateModel associated with the customer number sequence.
        If EntityStateModel is not present, a new model will be created.

        Parameters
        ----------
        raise_exception: bool
            Raises IntegrityError if Database cannot determine the next EntityStateModel available.

        Returns
        -------
        EntityStateModel
            The EntityStateModel associated with the CustomerModel number sequence.
        """
        EntityStateModel = lazy_loader.get_entity_state_model()

        try:
            LOOKUP = {
                'entity_model_id__exact': self.entity_model_id,
                'key__exact': EntityStateModel.KEY_CUSTOMER,
            }

            state_model_qs = EntityStateModel.objects.filter(**LOOKUP).select_for_update()
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
                'key': EntityStateModel.KEY_CUSTOMER,
                'sequence': 1,
            }
            state_model = EntityStateModel.objects.create(**LOOKUP)
            return state_model
        except IntegrityError as e:
            if raise_exception:
                raise e

    def generate_customer_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next Customer Number available.

        Parameters
        __________

        commit: bool
            Commits transaction into CustomerModel. Defaults to False.

        Returns
        _______
        str
            A String, representing the current CustomerModel instance Document Number.
        """
        if self.can_generate_customer_number():
            with transaction.atomic(durable=True):
                state_model = None
                while not state_model:
                    state_model = self._get_next_state_model(raise_exception=False)

            seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
            self.customer_number = f'{DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX}-{seq}'

            if commit:
                self.save(update_fields=['customer_number', 'updated'])

        return self.customer_number

    def validate_for_entity(self, entity_model: 'EntityModel'):  # noqa: F821
        if entity_model.uuid != self.entity_model_id:
            raise CustomerModelValidationError('EntityModel does not belong to this Vendor')

    def get_detail_url(self) -> str:
        return reverse('django_ledger:customer-detail',
                       kwargs={'customer_pk': self.uuid, 'entity_slug': self.entity_slug})

    def get_absolute_url(self) -> str:
        return self.get_detail_url()

    def get_update_url(self) -> str:
        return reverse('django_ledger:customer-update',
                       kwargs={'customer_pk': self.uuid, 'entity_slug': self.entity_slug})

    def clean(self):
        """
        Custom defined clean method that fetches the next customer number if not yet fetched.
        Additional validation may be provided.
        """
        if self.can_generate_customer_number():
            self.generate_customer_number(commit=False)

    def save(self, **kwargs):
        """
        Custom-defined save method that automatically fetches the customer number if not present.

        Parameters
        ----------
        kwargs
            Keywords passed to the super().save() method of the CustomerModel.
        """
        if not self.customer_number:
            self.generate_customer_number(commit=False)
        super(CustomerModelAbstract, self).save(**kwargs)


class CustomerModel(CustomerModelAbstract):
    """
    Base Customer Model Implementation
    """

    class Meta(CustomerModelAbstract.Meta):
        abstract = False
