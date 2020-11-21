"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from uuid import uuid4

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import ContactInfoMixIn, CreateUpdateMixIn


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


class VendorModel(ContactInfoMixIn, CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    vendor_name = models.CharField(max_length=100, unique=True)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Vendor Entity'),
                               related_name='vendors')
    description = models.TextField()
    active = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)

    additional_info = models.JSONField(null=True, blank=True)

    objects = VendorModelManager()

    class Meta:
        verbose_name = _('Vendor')
        indexes = [
            models.Index(fields=['created']),
            models.Index(fields=['updated']),
            models.Index(fields=['active']),
            models.Index(fields=['hidden']),
        ]

    def __str__(self):
        return f'Vendor: {self.vendor_name}'
