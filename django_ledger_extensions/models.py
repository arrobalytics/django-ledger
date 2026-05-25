"""
Country-agnostic regional infrastructure models.
"""
from __future__ import annotations

import hashlib
from uuid import uuid4

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import CreateUpdateMixIn


def supporting_document_upload_to(instance, filename: str) -> str:
    return f'django_ledger/supporting_documents/{instance.uuid}/{filename}'


class EntityTaxProfile(CreateUpdateMixIn):
    """
    Entity-level tax configuration consumed by country plugins.
    """

    class TaxRegime(models.TextChoices):
        STANDARD = 'standard', _('Standard')
        SMALL_BUSINESS = 'small_business', _('Small business exemption')
        EXEMPT = 'exempt', _('Tax exempt')

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.OneToOneField(
        'django_ledger.EntityModel',
        on_delete=models.CASCADE,
        related_name='tax_profile',
    )
    tax_regime = models.CharField(
        max_length=32,
        choices=TaxRegime.choices,
        default=TaxRegime.STANDARD,
    )
    default_vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        help_text=_('Default VAT rate as a decimal fraction, e.g. 0.19 for 19%.'),
    )
    vat_id = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        verbose_name = _('Entity Tax Profile')

    def __str__(self) -> str:
        return f'TaxProfile<{self.entity_id}:{self.tax_regime}>'


class SupportingDocumentModel(CreateUpdateMixIn):
    """
    Generic supporting document attached to ledger objects (JE, bill, invoice, …).
    """

    class DocumentType(models.TextChoices):
        RECEIPT = 'receipt', _('Receipt')
        INVOICE = 'invoice', _('Invoice')
        BANK_STATEMENT = 'bank_statement', _('Bank statement')
        CONTRACT = 'contract', _('Contract')
        OTHER = 'other', _('Other')

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    file = models.FileField(
        upload_to=supporting_document_upload_to,
        max_length=512,
    )
    document_type = models.CharField(
        max_length=32,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    description = models.CharField(max_length=512, blank=True, default='')
    checksum = models.CharField(max_length=64, blank=True, default='')
    immutable = models.BooleanField(
        default=False,
        help_text=_('When set, the file cannot be replaced or deleted.'),
    )

    class Meta:
        verbose_name = _('Supporting Document')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self) -> str:
        return f'SupportingDocument<{self.uuid}:{self.document_type}>'

    def save(self, *args, **kwargs):
        if self.file and not self.checksum:
            hasher = hashlib.sha256()
            for chunk in self.file.chunks():
                hasher.update(chunk)
            self.checksum = hasher.hexdigest()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.immutable:
            raise ValidationError(_('Immutable supporting documents cannot be deleted.'))
        return super().delete(*args, **kwargs)


class AccountTranslationModel(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    account = models.ForeignKey(
        'django_ledger.AccountModel',
        on_delete=models.CASCADE,
        related_name='translations',
    )
    locale = models.CharField(max_length=8)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = _('Account Translation')
        constraints = [
            models.UniqueConstraint(
                fields=['account', 'locale'],
                name='uniq_account_translation_locale',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.account_id}[{self.locale}]={self.name}'


class ItemTranslationModel(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    item = models.ForeignKey(
        'django_ledger.ItemModel',
        on_delete=models.CASCADE,
        related_name='translations',
    )
    locale = models.CharField(max_length=8)
    name = models.CharField(max_length=255)
    regional_code = models.CharField(max_length=32, blank=True, default='')

    class Meta:
        verbose_name = _('Item Translation')
        constraints = [
            models.UniqueConstraint(
                fields=['item', 'locale'],
                name='uniq_item_translation_locale',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.item_id}[{self.locale}]={self.name}'
