import json
from decimal import Decimal
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from django_ledger.models.entity import EntityModel
from django_ledger_extensions.payments import ExternalRefundPayload, import_external_refund


class Command(BaseCommand):
    help = 'Import an external refund against a prior payment (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument('--provider', required=True, help='Connector name, e.g. class_webapp')
        parser.add_argument('--external-id', required=True, help='Unique refund id from provider')
        parser.add_argument('--original-external-id', required=True, help='Original payment external id')
        parser.add_argument('--amount', required=True, help='Refund amount, e.g. 490.00')
        parser.add_argument('--refunded-at', required=True, help='ISO datetime')
        parser.add_argument('--reason', default='', help='Refund reason')
        parser.add_argument('--metadata-json', default='{}', help='Optional JSON metadata')

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        refunded_at = parse_datetime(options['refunded_at'])
        if refunded_at is None:
            raise CommandError(f'Invalid --refunded-at: {options["refunded_at"]}')

        payload = ExternalRefundPayload(
            provider=options['provider'],
            external_id=options['external_id'],
            original_external_id=options['original_external_id'],
            amount=Decimal(options['amount']),
            refunded_at=refunded_at,
            reason=options['reason'],
            metadata=json.loads(options['metadata_json']),
        )
        record = import_external_refund(entity, payload)
        self.stdout.write(
            self.style.SUCCESS(
                f'Refund {record.provider}:{record.external_id} → status={record.status} '
                f'invoice={record.invoice_id}'
            )
        )
        if record.error_message:
            self.stdout.write(self.style.WARNING(record.error_message))
