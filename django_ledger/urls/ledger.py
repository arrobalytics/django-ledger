from django.urls import path
from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/', views.LedgerModelListView.as_view(), name='ledger-list'),
    path('<slug:entity_slug>/create/', views.LedgerModelCreateView.as_view(), name='ledger-create'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/update/', views.LedgerModelUpdateView.as_view(), name='ledger-update'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/balance-sheet/',
         views.LedgerBalanceSheetView.as_view(),
         name='ledger-bs'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/income-statement/',
         views.LedgerIncomeStatementView.as_view(),
         name='ledger-ic'),
]
