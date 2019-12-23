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
    path('entity/<slug:entity_slug>/update/',
         views.EntityModelUpdateView.as_view(),
         name='entity-update'),

    # Financial Statements ---
    path('entity/<slug:entity_slug>/balance-sheet/',
         views.EntityBalanceSheetView.as_view(),
         name='entity-balance-sheet'),
    path('entity/<slug:entity_slug>/income-statement/',
         views.EntityIncomeStatementView.as_view(),
         name='entity-income-statement'),

    # Entity Chart of Accounts -----
    path('coa/<slug:entity_slug>/<slug:coa_slug>/update/',
         views.ChartOfAccountsUpdateView.as_view(),
         name='coa-update'),

    path('account/<slug:entity_slug>/<slug:coa_slug>/',
         views.AccountModelListView.as_view(),
         name='account-list'),
    path('account/<slug:entity_slug>/<slug:coa_slug>/create/',
         views.AccountModelCreateView.as_view(),
         name='account-create'),
    path('account/<slug:entity_slug>/<slug:coa_slug>/<int:account_pk>/update/',
         views.AccountModelUpdateView.as_view(),
         name='account-update'),

    # Ledger Views ----
    path('ledger/<slug:entity_slug>/',
         views.LedgerModelListView.as_view(),
         name='ledger-list'),
    path('ledger/<slug:entity_slug>/create/',
         views.LedgerModelCreateView.as_view(),
         name='ledger-create'),
    path('ledger/<slug:entity_slug>/<int:ledger_pk>/update/',
         views.LedgerModelUpdateView.as_view(),
         name='ledger-update'),
    path('ledger/<slug:entity_slug>/<slug:ledger_pk>/balance-sheet/',
         views.LedgerBalanceSheetView.as_view(),
         name='je-bs'),
    path('ledger/<slug:entity_slug>/<slug:ledger_pk>/income-statement/',
         views.LedgerIncomeStatementView.as_view(),
         name='je-ic'),

    # Journal Entry Views ----
    path('journal-entry/<slug:entity_slug>/<slug:ledger_pk>/',
         views.JournalEntryListView.as_view(),
         name='je-list'),
    path('journal-entry/<slug:entity_slug>/<slug:ledger_pk>/create/',
         views.JournalEntryCreateView.as_view(),
         name='je-create'),
    path('journal-entry/<slug:entity_slug>/<slug:ledger_pk>/<int:je_pk>/',
         views.JournalEntryDetailView.as_view(),
         name='je-detail'),
    path('journal-entry/<slug:entity_slug>/<slug:ledger_pk>/<int:je_pk>/update/',
         views.JournalEntryUpdateView.as_view(),
         name='je-update'),

    # TXS ----
    path('txs/<slug:entity_slug>/<slug:ledger_pk>/<int:je_pk>/txs/',
         views.TXSView.as_view(),
         name='txs'),

    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('', views.RootUrlView.as_view(), name='root-url')
]
