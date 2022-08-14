"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from calendar import month_name

from django.http import JsonResponse
from django.views.generic import View

from django_ledger.models import BillModel, EntityModel, InvoiceModel
from django_ledger.utils import accruable_net_summary
from django_ledger.views.mixins import LoginRequiredMixIn, EntityUnitMixIn


# from jsonschema import validate, ValidationError


class PnLAPIView(LoginRequiredMixIn, EntityUnitMixIn, View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            entity = EntityModel.objects.for_user(
                user_model=self.request.user).get(
                slug__exact=self.kwargs['entity_slug'])

            unit_slug = self.get_unit_slug()

            txs_qs, entity_digest = entity.digest(
                user_model=self.request.user,
                unit_slug=unit_slug,
                equity_only=True,
                signs=False,
                by_period=True,
                process_groups=True,
                from_date=self.request.GET.get('fromDate'),
                to_date=self.request.GET.get('toDate')
            )

            group_balance_by_period = entity_digest['tx_digest']['group_balance_by_period']
            group_balance_by_period = dict(sorted((k, v) for k, v in group_balance_by_period.items()))

            entity_data = {
                f'{month_name[k[1]]} {k[0]}': {d: float(f) for d, f in v.items()} for k, v in
                group_balance_by_period.items()}

            entity_pnl = {
                'entity_slug': entity.slug,
                'entity_name': entity.name,
                'pnl_data': entity_data
            }

            return JsonResponse({
                'results': entity_pnl
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)


class PayableNetAPIView(LoginRequiredMixIn, EntityUnitMixIn, View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            bill_qs = BillModel.objects.for_entity_unpaid(
                entity_slug=self.kwargs['entity_slug'],
                user_model=request.user,
            ).select_related('ledger__entity')

            # todo: implement this...
            # unit_slug = self.get_unit_slug()
            # if unit_slug:
            #     bill_qs.filter(ledger__journal_entry__entity_unit__slug__exact=unit_slug)

            net_summary = accruable_net_summary(bill_qs)
            entity_model = bill_qs.first().ledger.entity
            net_payables = {
                'entity_slug': self.kwargs['entity_slug'],
                'entity_name': entity_model.name,
                'net_payable_data': net_summary
            }

            return JsonResponse({
                'results': net_payables
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)


class ReceivableNetAPIView(LoginRequiredMixIn, EntityUnitMixIn, View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            invoice_qs = InvoiceModel.objects.for_entity_unpaid(
                entity_slug=self.kwargs['entity_slug'],
                user_model=request.user,
            ).select_related('ledger__entity')

            # todo: implement this...
            # unit_slug = self.get_unit_slug()
            # if unit_slug:
            #     invoice_qs.filter(ledger__journal_entry__entity_unit__slug__exact=unit_slug)

            net_summary = accruable_net_summary(invoice_qs)
            entity_model = invoice_qs.first().ledger.entity
            net_receivable = {
                'entity_slug': self.kwargs['entity_slug'],
                'entity_name': entity_model.name,
                'net_receivable_data': net_summary
            }

            return JsonResponse({
                'results': net_receivable
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)
