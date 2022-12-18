"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
    * Pranav P Tulshyan <ptulshyan77@gmail.com>

A Customer refers to the person or entity that buys product and services. When issuing Invoices, a Customer must be
created before it can be assigned to the InvoiceModel. Only customers who are active can be assigned to new Invoices.
"""

from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction, IntegrityError
from django.db.models import Q, F, QuerySet
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import ContactInfoMixIn, CreateUpdateMixIn, TaxCollectionMixIn
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX


class CustomerModelQueryset(QuerySet):
    """
    A custom defined QuerySet for the CustomerModel. This implements multiple methods or queries needed to get a
    filtered QuerySet based on the CustomerModel status. For example, we might want to have list of Customers that
    are active or hidden. All these separate functions will assist in making such queries and building customized
    reports.
    """

    def active(self) -> QuerySet:
        """
        Active customers can be assigned to new Invoices and show on dropdown menus and views.

        Returns
        -------
        CustomerModelQueryset
            A QuerySet of active Customers.
        """
        return self.filter(active=True)

    def inactive(self) -> QuerySet:
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

    def hidden(self) -> QuerySet:
        """
        Hidden customers do not show on dropdown menus, but may be used via APIs or any other method that does not
        involve the UI.

        Returns
        -------
        CustomerModelQueryset
            A QuerySet of hidden Customers.
        """
        return self.filter(hidden=True)

    def visible(self) -> QuerySet:
        """
        Visible customers show on dropdown menus and views. Visible customers are active and not hidden.

        Returns
        -------
        CustomerModelQueryset
            A QuerySet of visible Customers.
        """
        return self.filter(
            Q(hidden=False) & Q(active=True)
        )


class CustomerModelManager(models.Manager):
    """
    A custom defined CustomerModelManager that will act as an interface to handling the DB queries to the
    CustomerModel.
    """

    def for_user(self, user_model):
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

        Examples
        ________
            >>> request_user = request.user
            >>> customer_model_qs = CustomerModel.objects.for_user(user_model=request_user)
        """
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__admin=user_model) |
            Q(entity__managers__in=[user_model])
        )

    def for_entity(self, entity_slug, user_model) -> CustomerModelQueryset:
        """
        Fetches a QuerySet of CustomerModel associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        __________
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model
            Logged in and authenticated django UserModel instance.

        Examples
        ________
            >>> request_user = request.user
            >>> slug = kwargs['entity_slug'] # may come from request kwargs
            >>> customer_model_qs = CustomerModel.objects.for_entity(user_model=request_user, entity_slug=slug)

        Returns
        -------
        CustomerModelQueryset
            A filtered CustomerModel QuerySet.
        """
        qs = self.get_queryset()

        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return qs.filter(
                Q(entity=entity_slug) &
                Q(active=True) &
                (
                        Q(entity__admin=user_model) |
                        Q(entity__managers__in=[user_model])
                )
            )
        return qs.filter(
            Q(entity__slug__exact=entity_slug) &
            Q(active=True) &
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
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

    entity: EntityModel
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
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=30, editable=False, verbose_name=_('Customer Number'))

    # todo: rename to entity_model???...
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('Customer Entity'))
    description = models.TextField()
    active = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)

    additional_info = models.JSONField(null=True, blank=True)

    objects = CustomerModelManager.from_queryset(queryset_class=CustomerModelQueryset)()

    class Meta:
        abstract = True
        verbose_name = _('Customer')
        indexes = [
            models.Index(fields=['created']),
            models.Index(fields=['updated']),
            models.Index(fields=['active']),
            models.Index(fields=['hidden']),
            models.Index(fields=['customer_number']),
        ]
        unique_together = [
            ('entity', 'customer_number')
        ]

    def __str__(self):
        return f'Customer: {self.customer_name}'

    def can_generate_customer_number(self) -> bool:
        """
        Determines if the CustomerModel can be issued a Customer Number.
        CustomerModels have a unique sequential number, which is unique for each EntityMode/CustomerModel.

        Returns
        -------
        bool
            True if customer model can be generated, else False.
        """
        return all([
            self.entity_id,
            not self.customer_number
        ])

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
                'entity_id__exact': self.entity_id,
                'key__exact': EntityStateModel.KEY_CUSTOMER
            }

            state_model_qs = EntityStateModel.objects.filter(**LOOKUP).select_for_update()
            state_model = state_model_qs.get()
            state_model.sequence = F('sequence') + 1
            state_model.save()
            state_model.refresh_from_db()

            return state_model
        except ObjectDoesNotExist:

            LOOKUP = {
                'entity_id': self.entity_id,
                'entity_unit_id': None,
                'fiscal_year': None,
                'key': EntityStateModel.KEY_CUSTOMER,
                'sequence': 1
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
