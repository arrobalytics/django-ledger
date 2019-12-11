from django.urls import path

from . import views

app_name = 'django_ledger'

urlpatterns = [

    # Entity Views ----
    path('entity/',
         views.EntityModelListView.as_view(),
         name='entity-list'),
    path('entity/create/',
         views.EntityModelCreateView.as_view(),
         name='entity-create'),
    path('entity/<slug:entity_slug>/',
         views.EntityModelDetailVew.as_view(),
         name='entity-detail'),

    # Entity Chart of Accounts -----
    path('coa/<slug:coa_slug>/',
         views.ChartOfAccountsDetailView.as_view(),
         name='coa-detail'),

    # Accounts ---
    path('account/<int:account_pk>/',
         views.AccountModelDetailView.as_view(),
         name='account-detail'),
    path('account/create/',
         views.AccountCreateView.as_view(),
         name='account-create'),

    # Ledger Views ----
    path('entity/<slug:entity_slug>/ledger-list/',
         views.LedgerModelListView.as_view(),
         name='ledger-list'),
    path('entity/<slug:entity_slug>/ledger-create/',
         views.LedgerModelCreateView.as_view(),
         name='ledger-create'),
    path('entity/<slug:entity_slug>/ledger-update/<int:ledger_pk>/',
         views.LedgerModelUpdateView.as_view(),
         name='ledger-update'),
    path('entity/<slug:entity_slug>/ledger-detail/<int:ledger_pk>/',
         views.LedgerModelDetailView.as_view(),
         name='ledger-detail'),

    # Journal Entry Views ----
    path('entity/<slug:entity_slug>/ledger-detail/<slug:ledger_pk>/je-create/',
         views.JournalEntryCreateView.as_view(),
         name='je-create'),
    path('entity/<slug:entity_slug>/ledger-detail/<slug:ledger_pk>/je-update/<int:je_pk>/',
         views.JournalEntryUpdateView.as_view(),
         name='je-update'),
    path('entity/<slug:entity_slug>/ledger-detail/<slug:ledger_pk>/je-detail/<int:je_pk>/',
         views.JournalEntryDetailView.as_view(),
         name='je-detail'),

    # TXS ----
    path('entity/<slug:entity_slug>/ledger-detail/<slug:ledger_pk>/je-detail/<int:je_pk>/txs/',
         views.TXSIOView.as_view(),
         name='txs'),

    # Financial Statements ---
    path('entity/<slug:entity_slug>/balance-sheet/',
         views.EntityBalanceSheetView.as_view(),
         name='entity-balance-sheet'),
    path('entity/<slug:entity_slug>/income-statement/',
         views.EntityIncomeStatementView.as_view(),
         name='entity-income-statement'),

    path('', views.RootUrlView.as_view(), name='root-url')

]
