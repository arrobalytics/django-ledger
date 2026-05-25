import json
from dataclasses import asdict
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel
from django_ledger_countries.de.vat.reporting import (
    build_vat_quarterly_report,
    current_quarter,
    format_vat_quarterly_report,
)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)


class Command(BaseCommand):
    help = (
        'Quarterly VAT / turnover summary for ELSTER planning. '
        'Standard regime: Vorsteuer, Umsatzsteuer, expected payment. '
        'Kleinunternehmer / exempt: turnover tracking and threshold warnings.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument('--year', type=int, help='Calendar year (default: current year)')
        parser.add_argument('--quarter', type=int, choices=[1, 2, 3, 4], help='Quarter 1–4 (default: current)')
        parser.add_argument('--json', action='store_true', help='Output machine-readable JSON')

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        year = options.get('year')
        quarter = options.get('quarter')
        if year is None or quarter is None:
            default_year, default_quarter = current_quarter()
            year = year or default_year
            quarter = quarter or default_quarter

        report = build_vat_quarterly_report(entity, year=year, quarter=quarter)

        if options['json']:
            self.stdout.write(json.dumps(asdict(report), cls=DecimalEncoder, indent=2))
        else:
            self.stdout.write(format_vat_quarterly_report(report))
