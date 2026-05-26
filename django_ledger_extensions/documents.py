"""
Beleg inbox and supporting-document linking services.
"""
from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Optional, Union

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from django_ledger.models.utils import lazy_loader

from django_ledger_extensions.models import DocumentInboxItem, SupportingDocumentModel


def _checksum_file(file_obj) -> str:
    hasher = hashlib.sha256()
    for chunk in file_obj.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()


def create_inbox_item(
    entity,
    file,
    *,
    source: str = DocumentInboxItem.Source.UPLOAD,
    document_type: str = SupportingDocumentModel.DocumentType.RECEIPT,
    description: str = '',
    vendor_name: str = '',
    reference: str = '',
    suggested_amount: Optional[Decimal] = None,
    suggested_date: Optional[date] = None,
    external_source: str = '',
    external_id: str = '',
    metadata: Optional[dict] = None,
) -> DocumentInboxItem:
    if external_id:
        existing = DocumentInboxItem.objects.filter(
            entity=entity,
            external_source=external_source,
            external_id=external_id,
        ).first()
        if existing:
            return existing

    return DocumentInboxItem.objects.create(
        entity=entity,
        file=file,
        source=source,
        document_type=document_type,
        description=description,
        vendor_name=vendor_name,
        reference=reference,
        suggested_amount=suggested_amount,
        suggested_date=suggested_date,
        external_source=external_source,
        external_id=external_id,
        metadata=metadata or {},
    )


def attach_supporting_document(
    target,
    file,
    *,
    document_type: str = SupportingDocumentModel.DocumentType.RECEIPT,
    description: str = '',
) -> SupportingDocumentModel:
    return SupportingDocumentModel.objects.create(
        content_object=target,
        file=file,
        document_type=document_type,
        description=description,
    )


def _copy_file_to_supporting_document(inbox_item: DocumentInboxItem, target) -> SupportingDocumentModel:
    inbox_item.file.open('rb')
    try:
        content = inbox_item.file.read()
    finally:
        inbox_item.file.close()
    filename = inbox_item.file.name.rsplit('/', 1)[-1]
    doc = SupportingDocumentModel(
        content_type=ContentType.objects.get_for_model(target),
        object_id=target.pk,
        document_type=inbox_item.document_type,
        description=inbox_item.description,
        checksum=inbox_item.checksum or _checksum_file(ContentFile(content)),
    )
    doc.file.save(filename, ContentFile(content), save=True)
    return doc


@transaction.atomic
def link_inbox_item_to_object(
    inbox_item: DocumentInboxItem,
    target,
    *,
    archive_inbox: bool = False,
) -> SupportingDocumentModel:
    if inbox_item.status == DocumentInboxItem.Status.LINKED:
        raise ValidationError(_('This inbox item is already linked.'))
    if inbox_item.entity_id != _entity_id_for_target(target):
        raise ValidationError(_('Inbox item and ledger object belong to different entities.'))

    doc = _copy_file_to_supporting_document(inbox_item, target)
    inbox_item.status = DocumentInboxItem.Status.ARCHIVED if archive_inbox else DocumentInboxItem.Status.LINKED
    inbox_item.linked_content_type = ContentType.objects.get_for_model(target)
    inbox_item.linked_object_id = target.pk
    inbox_item.save(update_fields=['status', 'linked_content_type', 'linked_object_id', 'updated'])
    return doc


def _entity_id_for_target(target) -> Any:
    if hasattr(target, 'ledger_id') and target.ledger_id:
        return target.ledger.entity_id
    if hasattr(target, 'ledger') and target.ledger:
        return target.ledger.entity_id
    if hasattr(target, 'entity_id'):
        return target.entity_id
    if hasattr(target, 'entity_model_id'):
        return target.entity_model_id
    raise ValidationError(_('Cannot resolve entity for target object.'))


def iter_supporting_document_targets(journal_entry) -> Iterable:
    yield journal_entry
    ledger = getattr(journal_entry, 'ledger', None)
    if ledger is None:
        return
    get_wrapped = getattr(ledger, 'get_wrapped_model_instance', None)
    if not get_wrapped:
        return
    try:
        wrapped = get_wrapped()
    except Exception:
        wrapped = None
    if wrapped is not None:
        yield wrapped


def has_supporting_document_for_posting(journal_entry) -> bool:
    for target in iter_supporting_document_targets(journal_entry):
        ct = ContentType.objects.get_for_model(target)
        if SupportingDocumentModel.objects.filter(content_type=ct, object_id=target.pk).exists():
            return True
    return False


def suggest_inbox_matches(
    inbox_item: DocumentInboxItem,
    *,
    amount_tolerance: Decimal = Decimal('0.01'),
    day_tolerance: int = 7,
):
    """Return queryset of draft invoices on the same entity with similar amount."""
    InvoiceModel = lazy_loader.get_invoice_model()
    qs = InvoiceModel.objects.filter(
        ledger__entity_id=inbox_item.entity_id,
        invoice_status='draft',
    )
    if inbox_item.suggested_amount is not None:
        low = inbox_item.suggested_amount - amount_tolerance
        high = inbox_item.suggested_amount + amount_tolerance
        qs = qs.filter(amount_due__gte=low, amount_due__lte=high)
    return qs.order_by('-updated')[:10]


@transaction.atomic
def create_quick_expense(
    entity,
    *,
    amount: Decimal,
    expense_account,
    description: str,
    file: Optional[Union[UploadedFile, Any]] = None,
    credit_account=None,
    expense_date: Optional[date] = None,
    ledger_name: str = 'Manual expenses',
) -> tuple:
    """
    Create an unposted journal entry with optional Beleg in one step.

    Returns (journal_entry, supporting_document_or_none).
    """
    from django.utils.timezone import make_aware
    from datetime import datetime, time

    TransactionModel = lazy_loader.get_txs_model()
    JournalEntryModel = lazy_loader.get_journal_entry_model()
    LedgerModel = lazy_loader.get_ledger_model()

    if credit_account is None:
        credit_account = entity.default_coa.accountmodel_set.filter(code='1200 00', active=True).first()
        if credit_account is None:
            from django_ledger.io import roles

            credit_account = (
                entity.get_coa_accounts(active=True)
                .with_roles([roles.ASSET_CA_CASH])
                .is_role_default()
                .first()
            )
    if credit_account is None:
        raise ValidationError(_('No bank/cash account found for quick expense.'))

    expense_date = expense_date or date.today()
    timestamp = make_aware(datetime.combine(expense_date, time.min))

    ledger = LedgerModel.objects.filter(entity=entity, name=ledger_name).first()
    if ledger is None:
        ledger = LedgerModel(entity=entity, name=ledger_name, posted=False)
        ledger.save()

    je = JournalEntryModel(
        ledger=ledger,
        timestamp=timestamp,
        description=description,
        origin='manual',
    )
    je.clean(verify=False)
    je.save()

    debit_tx = TransactionModel(
        journal_entry=je,
        account=expense_account,
        amount=amount,
        tx_type='debit',
        description=description,
    )
    credit_tx = TransactionModel(
        journal_entry=je,
        account=credit_account,
        amount=amount,
        tx_type='credit',
        description=description,
    )
    debit_tx.clean()
    credit_tx.clean()
    TransactionModel.objects.bulk_create([debit_tx, credit_tx])

    doc = None
    if file is not None:
        doc = attach_supporting_document(je, file, description=description)
    return je, doc
