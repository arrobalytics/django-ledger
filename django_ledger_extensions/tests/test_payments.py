from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from django_ledger.models.utils import lazy_loader
from django_ledger.tests.base import DjangoLedgerBaseTest

from django_ledger_extensions.models import ExternalPaymentRecord, SupportingDocumentModel
from django_ledger_extensions.payments import ExternalPaymentPayload, import_external_payment


class ExternalPaymentImportTests(DjangoLedgerBaseTest):

    def test_import_creates_draft_invoice_idempotently(self):
        entity = self.get_random_entity_model()
        paid_at = timezone.now()
        payload = ExternalPaymentPayload(
            provider='class_webapp',
            external_id='pay_abc123',
            amount=Decimal('490.00'),
            paid_at=paid_at,
            customer_email='student@example.com',
            customer_name='Alex Student',
            product_name='Bildungsurlaub course',
            description='May 2026 cohort',
        )

        first = import_external_payment(entity, payload)
        second = import_external_payment(entity, payload)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.invoice_id, second.invoice_id)
        self.assertEqual(first.status, ExternalPaymentRecord.Status.INVOICE_DRAFT)
        self.assertEqual(
            ExternalPaymentRecord.objects.filter(
                entity=entity,
                provider='class_webapp',
                external_id='pay_abc123',
            ).count(),
            1,
        )

        invoice = first.invoice
        self.assertEqual(invoice.invoice_status, 'draft')
        self.assertEqual(invoice.amount_due, Decimal('490.00'))

        ItemTransactionModel = lazy_loader.get_item_transaction_model()
        lines = ItemTransactionModel.objects.filter(invoice_model=invoice)
        self.assertEqual(lines.count(), 1)
        self.assertEqual(lines.first().unit_cost, Decimal('490.00'))

    def test_import_with_receipt_links_supporting_document(self):
        entity = self.get_random_entity_model()
        payload = ExternalPaymentPayload(
            provider='class_webapp',
            external_id='pay_receipt_1',
            amount=Decimal('120.00'),
            paid_at=timezone.now(),
            customer_email='payer@example.com',
            receipt_file=SimpleUploadedFile('receipt.pdf', b'pdf-bytes', content_type='application/pdf'),
            receipt_description='Stripe receipt',
        )

        record = import_external_payment(entity, payload)
        invoice = record.invoice
        self.assertIsNotNone(invoice)
        self.assertTrue(
            SupportingDocumentModel.objects.filter(
                content_type__model='invoicemodel',
                object_id=invoice.pk,
            ).exists()
        )
        self.assertIsNotNone(record.inbox_item)
