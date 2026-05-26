import json
from decimal import Decimal
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from django_ledger.models.entity import EntityModel
from django_ledger_extensions.payments import ExternalPaymentPayload, import_external_payment


class Command(BaseCommand):
    help = 'Import an external class payment and create a draft invoice (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument('--provider', required=True, help='Connector name, e.g. class_webapp')
        parser.add_argument('--external-id', required=True, help='Unique payment id from provider')
        parser.add_argument('--amount', required=True, help='Payment amount, e.g. 490.00')
        parser.add_argument('--paid-at', required=True, help='ISO datetime, e.g. 2026-05-25T14:30:00')
        parser.add_argument('--customer-email', default='', help='Payer email')
        parser.add_argument('--customer-name', default='', help='Payer name')
        parser.add_argument('--product-name', default='Course fee', help='Line item name')
        parser.add_argument('--description', default='', help='Invoice description')
        parser.add_argument('--metadata-json', default='{}', help='Optional JSON metadata')
        parser.add_argument('--receipt', help='Optional path to receipt PDF/image to attach')

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        paid_at = parse_datetime(options['paid_at'])
        if paid_at is None:
            raise CommandError(f'Invalid --paid-at: {options["paid_at"]}')

        metadata = json.loads(options['metadata_json'])
        receipt_file = None
        if options.get('receipt'):
            receipt_file = open(options['receipt'], 'rb')

        payload = ExternalPaymentPayload(
            provider=options['provider'],
            external_id=options['external_id'],
            amount=Decimal(options['amount']),
            paid_at=paid_at,
            customer_email=options['customer_email'],
            customer_name=options['customer_name'],
            product_name=options['product_name'],
            description=options['description'],
            metadata=metadata,
            receipt_file=receipt_file,
        )
        try:
            record = import_external_payment(entity, payload)
        finally:
            if receipt_file is not None:
                receipt_file.close()

        self.stdout.write(
            self.style.SUCCESS(
                f'Payment {record.provider}:{record.external_id} → invoice {record.invoice_id} '
                f'(status={record.status}).'
            )
        )
