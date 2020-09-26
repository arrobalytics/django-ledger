from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import ContactInfoMixIn, CreateUpdateMixIn


class VendorModel(ContactInfoMixIn, CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    vendor_name = models.CharField(max_length=100)
    entity = models.ForeignKey('django_ledger.EntityModel', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Vendor')
        indexes = [
            models.Index(fields=['created']),
            models.Index(fields=['updated']),
        ]

    def __str__(self):
        return f'Vendor: {self.customer_name}'
