from django.urls import path

from django_ledger import views

urlpatterns = [
    path(
        'entity/<slug:entity_slug>/report/<slug:report_slug>/',
        views.EnterpriseReportAPIView.as_view(),
        name='enterprise-report-json',
    ),
    path(
        'entity/<slug:entity_slug>/report/<slug:report_slug>/csv/',
        views.EnterpriseReportCSVExportView.as_view(),
        name='enterprise-report-csv',
    ),
    path(
        'entity/<slug:entity_slug>/bank-statement/<uuid:statement_pk>/reconciliation/',
        views.BankReconciliationAPIView.as_view(),
        name='enterprise-bank-reconciliation-json',
    ),
    path(
        'entity/<slug:entity_slug>/budget-version/<uuid:budget_version_pk>/actuals/',
        views.BudgetVsActualAPIView.as_view(),
        name='enterprise-budget-vs-actual-json',
    ),
]
