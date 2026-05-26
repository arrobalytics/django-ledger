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
        STANDARD = 'standard', _('Standard VAT (Regelbesteuerung)')
        SMALL_BUSINESS = 'small_business', _('Kleinunternehmer (§ 19 UStG)')
        EXEMPT = 'exempt', _('Tax-exempt school / training (§ 4 UStG)')

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.OneToOneField(
        'django_ledger.EntityModel',
        on_delete=models.CASCADE,
        related_name='tax_profile',
    )
    tax_regime = models.CharField(
        max_length=32,
        choices=TaxRegime.choices,
        default=TaxRegime.EXEMPT,
        help_text=_(
            'Controls VAT posting behaviour. Change here when your Finanzamt '
            'confirms Kleinunternehmer or school exemption status.'
        ),
    )
    default_vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        help_text=_(
            'VAT rate as a decimal fraction (e.g. 0.19). Used only for the '
            'standard VAT regime.'
        ),
    )
    vat_id = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        verbose_name = _('Entity Tax Profile')

    def __str__(self) -> str:
        return f'TaxProfile<{self.entity_id}:{self.tax_regime}>'

    def clean(self):
        super().clean()
        if self.tax_regime == self.TaxRegime.STANDARD:
            if not self.default_vat_rate or self.default_vat_rate <= 0:
                raise ValidationError(
                    {'default_vat_rate': _('Standard VAT requires a positive default VAT rate.')}
                )
        elif self.default_vat_rate and self.default_vat_rate > 0:
            raise ValidationError(
                {
                    'default_vat_rate': _(
                        'Default VAT rate must be zero for exempt and Kleinunternehmer regimes.'
                    )
                }
            )


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


def document_inbox_upload_to(instance, filename: str) -> str:
    return f'django_ledger/document_inbox/{instance.uuid}/{filename}'


class DocumentInboxItem(CreateUpdateMixIn):
    """
    Staging area for Belege (receipts, PDFs) before they are linked to ledger objects.

    Supports email/camera/API ingestion without knowing journal entry or invoice UUIDs upfront.
    """

    class Source(models.TextChoices):
        UPLOAD = 'upload', _('Upload')
        EMAIL = 'email', _('Email')
        CAMERA = 'camera', _('Camera')
        API = 'api', _('API')
        WEBHOOK = 'webhook', _('Webhook')

    class Status(models.TextChoices):
        UNLINKED = 'unlinked', _('Unlinked')
        LINKED = 'linked', _('Linked')
        ARCHIVED = 'archived', _('Archived')

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.ForeignKey(
        'django_ledger.EntityModel',
        on_delete=models.CASCADE,
        related_name='document_inbox_items',
    )
    file = models.FileField(upload_to=document_inbox_upload_to, max_length=512)
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.UPLOAD)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.UNLINKED)
    document_type = models.CharField(
        max_length=32,
        choices=SupportingDocumentModel.DocumentType.choices,
        default=SupportingDocumentModel.DocumentType.RECEIPT,
    )
    description = models.CharField(max_length=512, blank=True, default='')
    vendor_name = models.CharField(max_length=255, blank=True, default='')
    reference = models.CharField(max_length=255, blank=True, default='')
    suggested_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    suggested_date = models.DateField(null=True, blank=True)
    external_source = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text=_('Third-party connector id, e.g. class_webapp, stripe, email-inbound.'),
    )
    external_id = models.CharField(max_length=255, blank=True, default='')
    checksum = models.CharField(max_length=64, blank=True, default='')
    linked_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_inbox_items_ct',
    )
    linked_object_id = models.UUIDField(null=True, blank=True)
    linked_object = GenericForeignKey('linked_content_type', 'linked_object_id')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _('Document Inbox Item')
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['external_source', 'external_id']),
            models.Index(fields=['linked_content_type', 'linked_object_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['entity', 'external_source', 'external_id'],
                condition=models.Q(external_id__gt=''),
                name='uniq_inbox_external_id_per_entity',
            ),
        ]

    def __str__(self) -> str:
        return f'Inbox<{self.uuid}:{self.status}>'

    def save(self, *args, **kwargs):
        if self.file and not self.checksum:
            hasher = hashlib.sha256()
            for chunk in self.file.chunks():
                hasher.update(chunk)
            self.checksum = hasher.hexdigest()
        super().save(*args, **kwargs)


class ExternalPaymentRecord(CreateUpdateMixIn):
    """
    Idempotent staging record for payments imported from a class webapp or other provider.

    Creates draft invoices and optional inbox/receipt attachments without coupling to a
    specific payment processor.
    """

    class Status(models.TextChoices):
        RECEIVED = 'received', _('Received')
        INVOICE_DRAFT = 'invoice_draft', _('Draft invoice created')
        FAILED = 'failed', _('Failed')

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.ForeignKey(
        'django_ledger.EntityModel',
        on_delete=models.CASCADE,
        related_name='external_payments',
    )
    provider = models.CharField(
        max_length=64,
        help_text=_('Connector name, e.g. class_webapp, stripe, paypal.'),
    )
    external_id = models.CharField(max_length=255)
    idempotency_key = models.CharField(max_length=255, blank=True, default='')
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    paid_at = models.DateTimeField()
    customer_email = models.EmailField(blank=True, default='')
    customer_name = models.CharField(max_length=255, blank=True, default='')
    product_name = models.CharField(max_length=255, blank=True, default='')
    description = models.CharField(max_length=512, blank=True, default='')
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.RECEIVED)
    error_message = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    invoice = models.ForeignKey(
        'django_ledger.InvoiceModel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='external_payment_records',
    )
    inbox_item = models.ForeignKey(
        DocumentInboxItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='external_payments',
    )

    class Meta:
        verbose_name = _('External Payment Record')
        constraints = [
            models.UniqueConstraint(
                fields=['entity', 'provider', 'external_id'],
                name='uniq_external_payment_per_entity',
            ),
        ]
        indexes = [
            models.Index(fields=['entity', 'provider']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f'ExternalPayment<{self.provider}:{self.external_id}>'


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
