from django.urls import path

from . import views

app_name = 'django_ledger'

urlpatterns = [
    path('entity/', views.EntityModelListView.as_view(), name='entity-list'),
    path('entity/<slug:entity_slug>/', views.EntityModelDetailVew.as_view(), name='entity-detail'),

    path('entity/<slug:entity_slug>/balance-sheet/',
         views.EntityBalanceSheetView.as_view(),
         name='entity-balance-sheet'),
    path('entity/<slug:entity_slug>/income-statement/',
         views.EntityIncomeStatementView.as_view(),
         name='entity-income-statement'),

    path('coa/<slug:coa_slug>/', views.ChartOfAccountsDetailView.as_view(), name='coa-detail'),
    path('account/<int:account_pk>/', views.AccountModelDetailView.as_view(), name='account-detail'),

]
