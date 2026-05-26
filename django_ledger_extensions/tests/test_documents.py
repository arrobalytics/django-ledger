from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from django_ledger.models.mixins import PaymentTermsMixIn
from django_ledger.models.utils import lazy_loader
from django_ledger.tests.base import DjangoLedgerBaseTest

from django_ledger_extensions.documents import (
    attach_supporting_document,
    create_inbox_item,
    create_quick_expense,
    has_supporting_document_for_posting,
    link_inbox_item_to_object,
)
from django_ledger_extensions.models import DocumentInboxItem, SupportingDocumentModel


UserModel = get_user_model()


class DocumentInboxTests(DjangoLedgerBaseTest):

    def test_create_and_link_inbox_item(self):
        entity = self.get_random_entity_model()
        uploaded = SimpleUploadedFile('receipt.jpg', b'fake-receipt-bytes', content_type='image/jpeg')
        inbox = create_inbox_item(
            entity,
            uploaded,
            description='Coffee receipt',
            suggested_amount=Decimal('12.50'),
        )
        self.assertEqual(inbox.status, DocumentInboxItem.Status.UNLINKED)
        self.assertTrue(inbox.checksum)

        je = self.get_random_je(entity, posted=False)
        doc = link_inbox_item_to_object(inbox, je)
        inbox.refresh_from_db()

        self.assertEqual(inbox.status, DocumentInboxItem.Status.LINKED)
        self.assertEqual(doc.content_object, je)
        self.assertEqual(doc.document_type, SupportingDocumentModel.DocumentType.RECEIPT)

    def test_inbox_external_id_is_idempotent(self):
        entity = self.get_random_entity_model()
        file_a = SimpleUploadedFile('a.pdf', b'a', content_type='application/pdf')
        file_b = SimpleUploadedFile('b.pdf', b'b', content_type='application/pdf')
        first = create_inbox_item(
            entity,
            file_a,
            external_source='email',
            external_id='msg-001',
        )
        second = create_inbox_item(
            entity,
            file_b,
            external_source='email',
            external_id='msg-001',
        )
        self.assertEqual(first.pk, second.pk)

    def test_has_supporting_document_on_wrapped_invoice(self):
        entity = self.get_random_entity_model()
        customer = entity.create_customer(
            {
                'customer_name': 'Student One',
                'email': 'student@example.com',
            }
        )
        invoice = entity.create_invoice(
            customer_model=customer,
            terms=PaymentTermsMixIn.TERMS_ON_RECEIPT,
            commit=True,
        )
        attach_supporting_document(
            invoice,
            SimpleUploadedFile('invoice.pdf', b'pdf', content_type='application/pdf'),
        )

        JournalEntryModel = lazy_loader.get_journal_entry_model()
        je = JournalEntryModel.objects.create(
            ledger=invoice.ledger,
            description='Payment receipt',
            origin='manual',
        )
        self.assertTrue(has_supporting_document_for_posting(je))

    def test_create_quick_expense_attaches_beleg(self):
        entity = self.get_random_entity_model()
        expense_account = entity.get_coa_accounts(active=True).expenses().first()
        self.assertIsNotNone(expense_account)

        je, doc = create_quick_expense(
            entity,
            amount=Decimal('25.00'),
            expense_account=expense_account,
            description='Office supplies',
            file=SimpleUploadedFile('supplies.jpg', b'img', content_type='image/jpeg'),
        )
        self.assertTrue(has_supporting_document_for_posting(je))
        self.assertIsNotNone(doc)
        self.assertEqual(je.transactionmodel_set.count(), 2)
