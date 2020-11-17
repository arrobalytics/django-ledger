from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/balance-sheet/year/<int:year>/',
         views.FiscalYearEntityModelBalanceSheetView.as_view(),
         name='entity-bs-year'),
    path('<slug:entity_slug>/balance-sheet/quarter/<int:year>/<str:quarter>/',
         views.QuarterlyEntityModelBalanceSheetView.as_view(),
         name='entity-bs-quarter'),
    path('<slug:entity_slug>/balance-sheet/month/<int:year>/<str:month>/',
         views.MonthlyEntityModelBalanceSheetView.as_view(),
         name='entity-bs-month'),
    path('<slug:entity_slug>/income-statement/year/<int:year>/',
         views.FiscalYearEntityModelIncomeStatementView.as_view(),
         name='entity-ic-year'),
    path('<slug:entity_slug>/income-statement/quarter/<int:year>/<str:quarter>/',
         views.QuarterlyEntityModelIncomeStatementView.as_view(),
         name='entity-ic-quarter'),
    path('<slug:entity_slug>/income-statement/month/<int:year>/<str:month>/',
         views.MonthlyEntityModelIncomeStatementView.as_view(),
         name='entity-ic-month'),
]
