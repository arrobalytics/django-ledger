"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import ContactInfoMixIn, CreateUpdateMixIn, BankAccountInfoMixIn, TaxInfoMixIn
from django_ledger.models.utils import LazyLoader
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING, DJANGO_LEDGER_VENDOR_NUMBER_PREFIX

lazy_loader = LazyLoader()


class VendorModelQuerySet(models.QuerySet):
    pass


class VendorModelManager(models.Manager):

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
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
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    vendor_number = models.CharField(max_length=30, null=True, blank=True)
    vendor_name = models.CharField(max_length=100)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Vendor Entity'),
                               related_name='vendors')
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

    def generate_vendor_number(self, commit: bool = False) -> str:
        """
        Atomic Transaction. Generates the next Vendor Number available.
        @param commit: Commit transaction into VendorModel.
        @return: A String, representing the current InvoiceModel instance Document Number.
        """
        if not self.vendor_number:
            with transaction.atomic():

                EntityStateModel = lazy_loader.get_entity_state_model()

                try:
                    LOOKUP = {
                        'entity_id__exact': self.entity_id,
                        'key__exact': EntityStateModel.KEY_VENDOR
                    }

                    state_model_qs = EntityStateModel.objects.select_related('entity').filter(**LOOKUP)
                    state_model = state_model_qs.get()
                    state_model.sequence += 1
                    state_model.save(update_fields=['sequence'])

                except ObjectDoesNotExist:

                    LOOKUP = {
                        'entity_id': self.entity_id,
                        'key': EntityStateModel.KEY_VENDOR,
                        'sequence': 1
                    }
                    state_model = EntityStateModel(**LOOKUP)
                    state_model.clean()
                    state_model.save()

            seq = str(state_model.sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
            self.vendor_number = f'{DJANGO_LEDGER_VENDOR_NUMBER_PREFIX}-{seq}'

            if commit:
                self.save(update_fields=['vendor_number'])

        return self.vendor_number

    def clean(self):
        if not self.vendor_number:
            self.generate_vendor_number(commit=False)

    def save(self, **kwargs):
        if not self.vendor_number:
            self.generate_vendor_number(commit=False)
        super(VendorModelAbstract, self).save(**kwargs)


class VendorModel(VendorModelAbstract):
    """
    Base Vendor Model Implamentation
    """
