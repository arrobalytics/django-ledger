"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

from calendar import month_name

from django.http import JsonResponse
from django.views.generic import View

from django_ledger.models import BillModel, EntityModel, InvoiceModel
from django_ledger.utils import accruable_net_summary
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, EntityUnitMixIn


class DjangoLedgerAPIViewBaseMixIn(DjangoLedgerSecurityMixIn, EntityUnitMixIn, View):
    """
    Shared security and entity scoping for dashboard chart API endpoints.
    """
    http_method_names = ['get']


class PnLAPIView(DjangoLedgerAPIViewBaseMixIn):
    """
    Returns profit-and-loss chart data for the business dashboard.
    """

    def get(self, request, *args, **kwargs):
        entity: EntityModel = self.get_authorized_entity_instance()
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
            # todo: For PnL to display proper period values must not use closing entries.
            use_closing_entries=False,
        )

        io_data = io_digest.get_io_data()
        group_balance_by_period = io_data['group_balance_by_period']
        group_balance_by_period = dict(
            sorted((k, v) for k, v in group_balance_by_period.items())
        )

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


class PayableNetAPIView(DjangoLedgerAPIViewBaseMixIn):
    """
    Returns unpaid bill aging data for the dashboard.
    """

    def get(self, request, *args, **kwargs):
        entity_model: EntityModel = self.get_authorized_entity_instance()
        bill_qs = BillModel.objects.for_entity(
            entity_model=entity_model
        ).unpaid()

        # todo: implement this...
        # unit_slug = self.get_unit_slug()
        # if unit_slug:
        #     bill_qs.filter(ledger__journal_entry__entity_unit__slug__exact=unit_slug)

        net_summary = accruable_net_summary(bill_qs)
        return JsonResponse(
            {
                'results': {
                    'entity_slug': entity_model.slug,
                    'entity_name': entity_model.name,
                    'net_payable_data': net_summary,
                }
            }
        )


class ReceivableNetAPIView(DjangoLedgerAPIViewBaseMixIn):
    """
    Returns unpaid invoice aging data for the dashboard.
    """

    def get(self, request, *args, **kwargs):
        entity_model: EntityModel = self.get_authorized_entity_instance()
        invoice_qs = InvoiceModel.objects.for_entity(
            entity_model=entity_model
        ).unpaid()

        # todo: implement this...
        # unit_slug = self.get_unit_slug()
        # if unit_slug:
        #     invoice_qs.filter(ledger__journal_entry__entity_unit__slug__exact=unit_slug)

        net_summary = accruable_net_summary(invoice_qs)
        return JsonResponse(
            {
                'results': {
                    'entity_slug': entity_model.slug,
                    'entity_name': entity_model.name,
                    'net_receivable_data': net_summary,
                }
            }
        )
