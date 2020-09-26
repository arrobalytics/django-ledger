from calendar import month_name

from django.http import JsonResponse
from django.views.generic import View

from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.utils import progressible_net_summary


class EntityPnLDataView(View):
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
                process_groups=True
            )

            group_balance_by_period = entity_digest['tx_digest']['group_balance_by_period']
            group_balance_by_period = dict(sorted((k,v) for k,v in group_balance_by_period.items()))
            entity_data = {
                f'{month_name[k[1]]} {k[0]}': {d: float(f) for d, f in v.items()} for k, v in
                group_balance_by_period.items()}
            return JsonResponse({
                'results': {
                    'entity_slug': entity.slug,
                    'entity_name': entity.name,
                    'pnl_data': entity_data
                }
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)


class EntityPayableNetDataView(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            bill_qs = BillModel.objects.for_entity_unpaid(
                entity_slug=self.kwargs['entity_slug'],
                user_model=request.user,
            )

            net_summary = progressible_net_summary(bill_qs)

            return JsonResponse({
                'results': {
                    'entity_slug': self.kwargs['entity_slug'],
                    'net_payable_data': net_summary
                }
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)


class EntityReceivableNetDataView(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            invoice_qs = InvoiceModel.objects.for_entity_unpaid(
                entity_slug=self.kwargs['entity_slug'],
                user_model=request.user,
            )

            net_summary = progressible_net_summary(invoice_qs)

            return JsonResponse({
                'results': {
                    'entity_slug': self.kwargs['entity_slug'],
                    'net_receivable_data': net_summary
                }
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)
