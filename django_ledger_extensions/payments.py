"""
Import course payments from external systems (class webapp, webhooks, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from django.core.exceptions import ValidationError
from django.utils.timezone import is_aware, make_aware

from django_ledger.models.mixins import PaymentTermsMixIn
from django_ledger.models.utils import lazy_loader

from django_ledger_extensions.documents import create_inbox_item, link_inbox_item_to_object
from django_ledger_extensions.models import DocumentInboxItem, ExternalPaymentRecord


@dataclass
class ExternalPaymentPayload:
    """Stable import contract for third-party connectors."""

    provider: str
    external_id: str
    amount: Decimal
    paid_at: datetime
    customer_email: str = ''
    customer_name: str = ''
    product_name: str = 'Course fee'
    description: str = ''
    currency: str = 'EUR'
    idempotency_key: str = ''
    metadata: dict = field(default_factory=dict)
    receipt_file: Any = None
    receipt_description: str = ''


@dataclass
class ExternalRefundPayload:
    """Idempotent refund event from a class webapp or payment provider."""

    provider: str
    external_id: str
    original_external_id: str
    amount: Decimal
    refunded_at: datetime
    reason: str = ''
    currency: str = 'EUR'
    metadata: dict = field(default_factory=dict)


def _default_uom(entity):
    uom = entity.unitofmeasuremodel_set.first()
    if uom:
        return uom
    return entity.unitofmeasuremodel_set.create(name='Unit', unit_abbr='ea')


def _get_or_create_customer(entity, *, email: str, name: str):
    CustomerModel = lazy_loader.get_customer_model()
    if email:
        match = CustomerModel.objects.filter(entity_model=entity, email__iexact=email).first()
        if match:
            return match
    display_name = name or email or 'Imported customer'
    return entity.create_customer(
        {
            'customer_name': display_name[:100],
            'email': email,
            'description': 'Imported from external payment',
            'additional_info': {'import_source': 'external_payment'},
        }
    )


def external_id_short(value: str) -> str:
    return (value or 'unknown')[:8]


def _get_or_create_course_item(entity, product_name: str):
    ItemModel = lazy_loader.get_item_model()
    name = product_name or 'Course fee'
    existing = ItemModel.objects.filter(entity=entity, name=name).services().first()
    if existing:
        return existing
    return entity.create_item_service(name=name, uom_model=_default_uom(entity))


def import_external_payment(entity, payload: ExternalPaymentPayload) -> ExternalPaymentRecord:
    """
    Idempotently create a draft invoice (and optional receipt) from an external payment.

    Intended to be called from your class webapp, a webhook view, or a management command.
    """
    paid_at = payload.paid_at
    if not is_aware(paid_at):
        paid_at = make_aware(paid_at)

    record, created = ExternalPaymentRecord.objects.get_or_create(
        entity=entity,
        provider=payload.provider,
        external_id=payload.external_id,
        defaults={
            'idempotency_key': payload.idempotency_key,
            'amount': payload.amount,
            'currency': payload.currency,
            'paid_at': paid_at,
            'customer_email': payload.customer_email,
            'customer_name': payload.customer_name,
            'product_name': payload.product_name,
            'description': payload.description,
            'metadata': payload.metadata,
        },
    )
    if not created and record.invoice_id:
        return record

    try:
        customer = _get_or_create_customer(
            entity,
            email=payload.customer_email,
            name=payload.customer_name,
        )
        item = _get_or_create_course_item(entity, payload.product_name)
        invoice = entity.create_invoice(
            customer_model=customer,
            terms=PaymentTermsMixIn.TERMS_ON_RECEIPT,
            date_draft=paid_at.date(),
            ledger_name=f'{payload.provider} {payload.external_id}',
            additional_info={
                'external_payment': {
                    'provider': payload.provider,
                    'external_id': payload.external_id,
                    'paid_at': paid_at.isoformat(),
                    **payload.metadata,
                }
            },
            commit=True,
        )
        ItemTransactionModel = lazy_loader.get_item_transaction_model()
        line = ItemTransactionModel(
            invoice_model=invoice,
            item_model=item,
            quantity=Decimal('1'),
            unit_cost=payload.amount,
        )
        line.full_clean()
        line.save()
        invoice.update_amount_due(itemtxs_qs=[line])
        invoice.save(
            update_fields=['amount_due', 'amount_receivable', 'amount_unearned', 'amount_earned', 'updated']
        )

        record.invoice = invoice
        record.status = ExternalPaymentRecord.Status.INVOICE_DRAFT
        record.error_message = ''

        if payload.receipt_file is not None:
            from django_ledger_extensions.models import SupportingDocumentModel

            inbox = create_inbox_item(
                entity,
                payload.receipt_file,
                source=DocumentInboxItem.Source.WEBHOOK,
                document_type=SupportingDocumentModel.DocumentType.RECEIPT,
                description=payload.receipt_description or payload.description,
                suggested_amount=payload.amount,
                suggested_date=paid_at.date(),
                external_source=payload.provider,
                external_id=f'{payload.external_id}:receipt',
                metadata={'payment_external_id': payload.external_id},
            )
            record.inbox_item = inbox
            link_inbox_item_to_object(inbox, invoice)

        record.save(
            update_fields=['invoice', 'status', 'error_message', 'inbox_item', 'updated']
        )
    except Exception as exc:
        record.status = ExternalPaymentRecord.Status.FAILED
        record.error_message = str(exc)
        record.save(update_fields=['status', 'error_message', 'updated'])
        raise ValidationError(str(exc)) from exc

    return record


def import_external_refund(entity, payload: ExternalRefundPayload) -> ExternalPaymentRecord:
    """
    Idempotently record a refund against a prior ``import_external_payment``.

    Draft/review invoices are canceled; approved (unpaid) invoices are voided.
    Paid invoices are flagged for manual void/credit in the ledger UI.
    """
    refunded_at = payload.refunded_at
    if not is_aware(refunded_at):
        refunded_at = make_aware(refunded_at)

    original = ExternalPaymentRecord.objects.filter(
        entity=entity,
        provider=payload.provider,
        external_id=payload.original_external_id,
        record_type=ExternalPaymentRecord.RecordType.PAYMENT,
    ).first()
    if original is None or not original.invoice_id:
        raise ValidationError(
            f'Original payment not found: {payload.provider}:{payload.original_external_id}'
        )

    record, created = ExternalPaymentRecord.objects.get_or_create(
        entity=entity,
        provider=payload.provider,
        external_id=payload.external_id,
        defaults={
            'record_type': ExternalPaymentRecord.RecordType.REFUND,
            'amount': payload.amount,
            'currency': payload.currency,
            'paid_at': refunded_at,
            'description': payload.reason,
            'metadata': payload.metadata,
            'original_payment': original,
            'invoice': original.invoice,
        },
    )
    if not created and record.status in (
        ExternalPaymentRecord.Status.REFUND_APPLIED,
        ExternalPaymentRecord.Status.MANUAL_ACTION_REQUIRED,
    ):
        return record

    invoice = original.invoice
    entity_slug = entity.slug
    user_model = entity.admin

    try:
        if invoice.is_draft() or invoice.is_review():
            invoice.mark_as_canceled(date_canceled=refunded_at.date(), commit=True)
            record.status = ExternalPaymentRecord.Status.REFUND_APPLIED
            record.error_message = ''
        elif invoice.can_void():
            invoice.mark_as_void(
                entity_slug=entity_slug,
                user_model=user_model,
                date_void=refunded_at.date(),
                commit=True,
            )
            record.status = ExternalPaymentRecord.Status.REFUND_APPLIED
            record.error_message = ''
        elif invoice.is_paid() or invoice.is_approved():
            record.status = ExternalPaymentRecord.Status.MANUAL_ACTION_REQUIRED
            record.error_message = (
                'Invoice was approved/paid — void or issue a credit note manually in the ledger UI.'
            )
        else:
            record.status = ExternalPaymentRecord.Status.MANUAL_ACTION_REQUIRED
            record.error_message = f'Invoice status {invoice.invoice_status} — handle refund manually.'

        record.save(update_fields=['status', 'error_message', 'updated'])
    except Exception as exc:
        record.status = ExternalPaymentRecord.Status.FAILED
        record.error_message = str(exc)
        record.save(update_fields=['status', 'error_message', 'updated'])
        raise ValidationError(str(exc)) from exc

    return record
