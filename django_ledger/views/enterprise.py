"""
JSON and export views for enterprise accounting workflows.
"""
from __future__ import annotations

from django.http import Http404, HttpResponse, JsonResponse
from django.utils.dateparse import parse_date
from django.views.generic import View

from django_ledger.models import EntityModel
from django_ledger.report.enterprise import (
    get_ap_aging_data,
    get_ar_aging_data,
    get_audit_log_export_data,
    get_bank_reconciliation_data,
    get_budget_vs_actual_data,
    get_depreciation_summary,
    get_fixed_asset_register,
    get_general_ledger_data,
    get_tax_summary_data,
    get_trial_balance_data,
)
from django_ledger.services.enterprise import export_rows_to_csv, require_report_access
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


def _date_param(request, name):
    value = request.GET.get(name)
    return parse_date(value) if value else None


def _serialize_rows(rows):
    return [dict(row) for row in rows]


class EnterpriseReportAPIView(DjangoLedgerSecurityMixIn, View):
    http_method_names = ['get']

    report_map = {
        'trial-balance': get_trial_balance_data,
        'general-ledger': get_general_ledger_data,
        'ar-aging': get_ar_aging_data,
        'ap-aging': get_ap_aging_data,
        'tax-summary': get_tax_summary_data,
        'audit-log': get_audit_log_export_data,
        'fixed-asset-register': get_fixed_asset_register,
        'depreciation-summary': get_depreciation_summary,
    }

    def get_entity_model(self):
        return EntityModel.objects.for_user(user_model=self.request.user).get(slug__exact=self.kwargs['entity_slug'])

    def get_report_data(self, entity_model, report_slug):
        from_date = _date_param(self.request, 'fromDate')
        to_date = _date_param(self.request, 'toDate')
        as_of_date = _date_param(self.request, 'asOfDate')
        if report_slug == 'ar-aging':
            return get_ar_aging_data(entity_model, as_of_date=as_of_date)
        if report_slug == 'ap-aging':
            return get_ap_aging_data(entity_model, as_of_date=as_of_date)
        if report_slug in ['trial-balance', 'general-ledger', 'tax-summary', 'audit-log']:
            return self.report_map[report_slug](entity_model, from_date=from_date, to_date=to_date)
        if report_slug in self.report_map:
            return self.report_map[report_slug](entity_model)
        raise Http404('Unknown enterprise report.')

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'message': 'Unauthorized'}, status=401)
        entity_model = self.get_entity_model()
        require_report_access(request.user, entity_model)
        report_slug = kwargs['report_slug']
        rows = self.get_report_data(entity_model, report_slug)
        return JsonResponse({
            'results': {
                'entity_slug': entity_model.slug,
                'entity_name': entity_model.name,
                'report': report_slug,
                'data': _serialize_rows(rows),
            }
        })


class EnterpriseReportCSVExportView(EnterpriseReportAPIView):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'message': 'Unauthorized'}, status=401)
        entity_model = self.get_entity_model()
        require_report_access(request.user, entity_model)
        report_slug = kwargs['report_slug']
        rows = _serialize_rows(self.get_report_data(entity_model, report_slug))
        fieldnames = sorted({key for row in rows for key in row.keys()})
        csv_text = export_rows_to_csv(rows, fieldnames) if fieldnames else ''
        response = HttpResponse(csv_text, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_slug}.csv"'
        return response


class BankReconciliationAPIView(DjangoLedgerSecurityMixIn, View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'message': 'Unauthorized'}, status=401)
        from django_ledger.models import BankStatementModel

        entity_model = EntityModel.objects.for_user(user_model=request.user).get(slug__exact=kwargs['entity_slug'])
        require_report_access(request.user, entity_model)
        statement_model = BankStatementModel.objects.for_entity(entity_model).get(uuid=kwargs['statement_pk'])
        data = get_bank_reconciliation_data(statement_model)
        return JsonResponse({
            'results': {
                'statement': str(data['statement'].uuid),
                'matched': _serialize_rows(data['matched'].values()),
                'unmatched': _serialize_rows(data['unmatched'].values()),
                'ignored': _serialize_rows(data['ignored'].values()),
            }
        })


class BudgetVsActualAPIView(DjangoLedgerSecurityMixIn, View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'message': 'Unauthorized'}, status=401)
        from django_ledger.models import BudgetVersionModel

        entity_model = EntityModel.objects.for_user(user_model=request.user).get(slug__exact=kwargs['entity_slug'])
        require_report_access(request.user, entity_model)
        budget_version = BudgetVersionModel.objects.for_entity(entity_model).get(uuid=kwargs['budget_version_pk'])
        return JsonResponse({
            'results': {
                'entity_slug': entity_model.slug,
                'budget_version': str(budget_version.uuid),
                'data': _serialize_rows(get_budget_vs_actual_data(budget_version)),
            }
        })
