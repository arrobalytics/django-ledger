"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

JSON API endpoints for dashboard widgets (PnL, payables, receivables).

All endpoints:
  * Require login + entity authorization via DjangoLedgerSecurityMixIn
  * Scope querysets to the authorized entity only
  * Return GET-only JSON (no mutations)
"""

from calendar import month_name

from django.http import JsonResponse
from django.views.generic import View

from django_ledger.models import BillModel, InvoiceModel
from django_ledger.utils import accruable_net_summary
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, EntityUnitMixIn


class PnLAPIView(DjangoLedgerSecurityMixIn, EntityUnitMixIn, View):
    """
    RETRIEVE — Profit & Loss digest by period for the authorized entity.

    Optional query params: fromDate, toDate. Optional unit via EntityUnitMixIn.
    """

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        entity = self.get_authorized_entity_instance()
        unit_slug = self.get_unit_slug()

        io_digest = entity.digest(
            user_model=self.request.user,
            unit_slug=unit_slug,
            equity_only=True,
            signs=False,
            by_period=True,
            process_groups=True,
            from_date=self.request.GET.get('fromDate'),
            to_date=self.request.GET.get('toDate'),
            # PnL period values must not use closing entries.
            use_closing_entries=False,
        )

        io_data = io_digest.get_io_data()
        group_balance_by_period = io_data['group_balance_by_period']
        group_balance_by_period = dict(sorted((k, v) for k, v in group_balance_by_period.items()))

        entity_data = {
            f'{month_name[k[1]]} {k[0]}': {d: float(f) for d, f in v.items()}
            for k, v in group_balance_by_period.items()
        }

        return JsonResponse(
            {
                'results': {
                    'entity_slug': entity.slug,
                    'entity_name': entity.name,
                    'pnl_data': entity_data,
                }
            }
        )


class PayableNetAPIView(DjangoLedgerSecurityMixIn, EntityUnitMixIn, View):
    """
    RETRIEVE — Net payable aging summary for unpaid bills of the entity.

    Returns an empty summary payload when there are no unpaid bills
    (avoids leaking errors / 500s on empty data).
    """

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        entity = self.get_authorized_entity_instance()
        bill_qs = BillModel.objects.for_entity(entity_model=entity).unpaid()

        # todo: filter by unit_slug when JE/unit linkage is available on bills.
        # unit_slug = self.get_unit_slug()

        if not bill_qs.exists():
            return JsonResponse(
                {
                    'results': {
                        'entity_slug': entity.slug,
                        'entity_name': entity.name,
                        'net_payable_data': {},
                    }
                }
            )

        net_summary = accruable_net_summary(bill_qs)
        return JsonResponse(
            {
                'results': {
                    'entity_slug': entity.slug,
                    'entity_name': entity.name,
                    'net_payable_data': net_summary,
                }
            }
        )


class ReceivableNetAPIView(DjangoLedgerSecurityMixIn, EntityUnitMixIn, View):
    """
    RETRIEVE — Net receivable aging summary for unpaid invoices of the entity.

    Returns an empty summary payload when there are no unpaid invoices.
    """

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        entity = self.get_authorized_entity_instance()
        invoice_qs = InvoiceModel.objects.for_entity(entity_model=entity).for_user(self.request.user).unpaid()

        # todo: filter by unit_slug when JE/unit linkage is available on invoices.

        if not invoice_qs.exists():
            return JsonResponse(
                {
                    'results': {
                        'entity_slug': entity.slug,
                        'entity_name': entity.name,
                        'net_receivable_data': {},
                    }
                }
            )

        net_summary = accruable_net_summary(invoice_qs)
        return JsonResponse(
            {
                'results': {
                    'entity_slug': entity.slug,
                    'entity_name': entity.name,
                    'net_receivable_data': net_summary,
                }
            }
        )
