from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel

from django_ledger_extensions.bank_matching import auto_match_external_payments, suggest_staged_transaction_matches
from django_ledger_extensions.models import ExternalPaymentRecord


class Command(BaseCommand):
    help = 'Suggest or auto-link webapp payments to bank import staged transactions.'

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument('--payment', help='ExternalPaymentRecord UUID')
        parser.add_argument('--apply', action='store_true', help='Auto-link unique matches')
        parser.add_argument('--limit', type=int, default=50, help='Max payments to process with --apply')

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        if options.get('payment'):
            try:
                record = ExternalPaymentRecord.objects.get(uuid=options['payment'], entity=entity)
            except ExternalPaymentRecord.DoesNotExist as exc:
                raise CommandError(f'Payment record not found: {options["payment"]}') from exc
            matches = suggest_staged_transaction_matches(record)
            if not matches:
                self.stdout.write('No staged transaction matches found.')
                return
            for match in matches:
                self.stdout.write(
                    f'  {match.uuid}  {match.date_posted}  {match.amount or match.amount_split}  {match.name or match.memo}'
                )
            return

        if options['apply']:
            linked = auto_match_external_payments(entity, limit=options['limit'])
            self.stdout.write(self.style.SUCCESS(f'Linked {len(linked)} payment(s).'))
            return

        qs = ExternalPaymentRecord.objects.filter(
            entity=entity,
            record_type=ExternalPaymentRecord.RecordType.PAYMENT,
            staged_transaction__isnull=True,
        ).order_by('-paid_at')[: options['limit']]
        for record in qs:
            matches = suggest_staged_transaction_matches(record, limit=3)
            self.stdout.write(
                f'{record.provider}:{record.external_id} €{record.amount} → {len(matches)} candidate(s)'
            )
