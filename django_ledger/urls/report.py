from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/balance-sheet/',
         views.EntityModelBalanceSheetView.as_view(),
         name='entity-bs'),
    path('<slug:entity_slug>/income-statement/year/<int:year>/',
         views.FiscalYearEntityIncomeStatementView.as_view(),
         name='entity-ic-year'),
    path('<slug:entity_slug>/income-statement/quarter/<int:year>/<str:quarter>/',
         views.QuarterlyEntityIncomeStatementView.as_view(),
         name='entity-ic-quarter'),
    path('<slug:entity_slug>/income-statement/month/<int:year>/<str:month>/',
         views.MonthlyEntityIncomeStatementView.as_view(),
         name='entity-ic-month'),
]
