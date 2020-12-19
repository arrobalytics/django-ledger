"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from calendar import month_name

from django.http import JsonResponse
from django.views.generic import View
from jsonschema import validate, ValidationError

from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.schemas import SCHEMA_PNL, SCHEMA_NET_PAYABLES, SCHEMA_NET_RECEIVABLE
from django_ledger.settings import DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME
from django_ledger.utils import progressible_net_summary


class EntityProfitNLossAPIView(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            entity = EntityModel.objects.for_user(
                user_model=self.request.user).get(
                slug__exact=self.kwargs['entity_slug'])

            entity_digest = entity.digest(
                user_model=self.request.user,
                equity_only=True,
                signs=False,
                by_period=True,
                process_groups=True,
                from_date=self.request.GET.get('startDate'),
                to_date=self.request.GET.get('endDate')
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

            if DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME:
                try:
                    validate(instance=entity_pnl, schema=SCHEMA_PNL)
                except ValidationError as e:
                    return JsonResponse({
                        'message': f'Schema validation error. {e.message}'
                    }, status=500)

            return JsonResponse({
                'results': entity_pnl
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)


class EntityPayableNetAPIView(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:

            bill_qs = BillModel.objects.for_entity_unpaid(
                entity_slug=self.kwargs['entity_slug'],
                user_model=request.user,
            ).select_related('ledger__entity')

            net_summary = progressible_net_summary(bill_qs)
            entity_model = bill_qs.first().ledger.entity
            net_payables = {
                'entity_slug': self.kwargs['entity_slug'],
                'entity_name': entity_model.name,
                'net_payable_data': net_summary
            }

            if DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME:
                try:
                    validate(instance=net_payables, schema=SCHEMA_NET_PAYABLES)
                except ValidationError as e:
                    return JsonResponse({
                        'message': f'Schema validation error. {e.message}'
                    }, status=500)

            return JsonResponse({
                'results': net_payables
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)


class EntityReceivableNetAPIView(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            invoice_qs = InvoiceModel.objects.for_entity_unpaid(
                entity_slug=self.kwargs['entity_slug'],
                user_model=request.user,
            ).select_related('ledger__entity')

            net_summary = progressible_net_summary(invoice_qs)
            entity_model = invoice_qs.first().ledger.entity
            net_receivable = {
                'entity_slug': self.kwargs['entity_slug'],
                'entity_name': entity_model.name,
                'net_receivable_data': net_summary
            }

            if DJANGO_LEDGER_VALIDATE_SCHEMAS_AT_RUNTIME:
                try:
                    validate(instance=net_receivable, schema=SCHEMA_NET_RECEIVABLE)
                except ValidationError as e:
                    return JsonResponse({
                        'message': f'Schema validation error. {e.message}'
                    }, status=500)

            return JsonResponse({
                'results': net_receivable
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)
