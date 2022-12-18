"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

A Vendor refers to the person or entity that provides products and services to the business for a fee.
Vendors are an integral part of the billing process as they are the providers of goods and services for the
business.

Vendors can be flagged as active/inactive or hidden. Vendors who no longer conduct business with the EntityModel,
whether temporarily or indefinitely may be flagged as inactive (i.e. active is False). Hidden Vendors will not show up
as an option in the UI, but can still be used programmatically (via API).
"""

from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction, IntegrityError
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import ContactInfoMixIn, CreateUpdateMixIn, BankAccountInfoMixIn, TaxInfoMixIn
from django_ledger.models.utils import lazy_loader
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_VENDOR_NUMBER_PREFIX


class VendorModelQuerySet(models.QuerySet):
    """
    Custom defined VendorModel QuerySet.
    """


class VendorModelManager(models.Manager):
    """
    Custom defined VendorModel Manager, which defines many methods for initial query of the Database.
    """

    def for_entity(self, entity_slug, user_model) -> VendorModelQuerySet:
        """
        Fetches a QuerySet of VendorModel associated with a specific EntityModel & UserModel.
        May pass an instance of EntityModel or a String representing the EntityModel slug.

        Parameters
        ----------
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model
            Logged in and authenticated django UserModel instance.

        Examples
        ________
            >>> request_user = request.user
            >>> slug = kwargs['entity_slug'] # may come from request kwargs
            >>> vendor_model_qs = VendorModel.objects.for_entity(user_model=request_user, entity_slug=slug)

        Returns
        -------
        VendorModelQuerySet
            A filtered VendorModel QuerySet.
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


class VendorModelAbstract(ContactInfoMixIn,
                          BankAccountInfoMixIn,
                          TaxInfoMixIn,
                          CreateUpdateMixIn):

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

    entity: EntityModel
        The EntityModel associated with this Vendor.

    vendor_name: str
        A string representing the name the customer uses to do business with the EntityModel.

    vendor_number: str
        A unique, auto-generated human-readable number which identifies the vendor within the EntityModel.

    description: str
        A text field to capture the description about the vendor.

    active: bool
        We can set any customer code to be active or inactive. Defaults to True.

    hidden: bool
        Hidden VendorModel don't show on the UI. Defaults to False.

    additional_info: dict
        Any additional information about the vendor, stored as a JSON object using a JSONField.


    """
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    vendor_number = models.CharField(max_length=30, null=True, blank=True)
    vendor_name = models.CharField(max_length=100)

    # todo: rename to entity_model?...
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Vendor Entity'))
    description = models.TextField()
    active = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)

    additional_info = models.JSONField(null=True, blank=True)

    objects = VendorModelManager.from_queryset(queryset_class=VendorModelQuerySet)()

    class Meta:
        verbose_name = _('Vendor')
        indexes = [
            models.Index(fields=['created']),
            models.Index(fields=['updated']),
            models.Index(fields=['active']),
            models.Index(fields=['hidden']),
        ]
        unique_together = [
            ('entity', 'vendor_number')
        ]
        abstract = True

    def __str__(self):
        return f'Vendor: {self.vendor_name}'

    def can_generate_vendor_number(self) -> bool:
        """
        Determines if the VendorModel can be issued a Vendor Number.
        VendorModel have a unique sequential number, which is unique for each EntityModel/VendorModel.

        Returns
        -------
        bool
            True if customer model can be generated, else False.
        """
        return all([
            self.entity_id,
            not self.vendor_number
        ])

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
                'entity_id__exact': self.entity_id,
                'key__exact': EntityStateModel.KEY_VENDOR
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
                'key': EntityStateModel.KEY_VENDOR,
                'sequence': 1
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
