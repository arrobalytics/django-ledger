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
    path('entity/set-default/',
         views.SetDefaultEntityView.as_view(),
         name='entity-set-default'),
    path('entity/<slug:entity_slug>/dashboard/',
         views.EntityModelDashboardView.as_view(),
         name='entity-dashboard'),
    path('entity/<slug:entity_slug>/manage/',
         views.EntityModelManageView.as_view(),
         name='entity-manage'),
    path('entity/<slug:entity_slug>/set-date/',
         views.SetDateView.as_view(),
         name='entity-set-date'),
    path('entity/<slug:entity_slug>/generate-sample-data/',
         views.GenerateSampleData.as_view(),
         name='entity-generate-sample-data'),

    # Entity JSON Data Layer ----
    path('entity/<slug:entity_slug>/data/pnl/',
         views.EntityPnLDataView.as_view(),
         name='entity-json-pnl'),
    path('entity/<slug:entity_slug>/data/net-payables/',
         views.EntityPayableNetDataView.as_view(),
         name='entity-json-net-payables'),
    path('entity/<slug:entity_slug>/data/net-receivables/',
         views.EntityReceivableNetDataView.as_view(),
         name='entity-json-net-receivables'),

    # Financial Statements ---
    path('entity/<slug:entity_slug>/balance-sheet/',
         views.EntityModelBalanceSheetView.as_view(),
         name='entity-bs'),
    path('entity/<slug:entity_slug>/income-statement/',
         views.EntityModelIncomeStatementView.as_view(),
         name='entity-ic'),

    # Entity Chart of Accounts -----
    path('coa/<slug:entity_slug>/<slug:coa_slug>/update/',
         views.ChartOfAccountsUpdateView.as_view(),
         name='coa-update'),

    # Accounts ---
    path('account/<slug:entity_slug>/<slug:coa_slug>/',
         views.AccountModelListView.as_view(),
         name='account-list'),
    path('account/<slug:entity_slug>/<slug:coa_slug>/create/',
         views.AccountModelCreateView.as_view(),
         name='account-create'),
    path('account/<slug:entity_slug>/<slug:coa_slug>/<uuid:account_pk>/update/',
         views.AccountModelUpdateView.as_view(),
         name='account-update'),

    # Ledger Views ----
    path('ledger/<slug:entity_slug>/',
         views.LedgerModelListView.as_view(),
         name='ledger-list'),
    path('ledger/<slug:entity_slug>/create/',
         views.LedgerModelCreateView.as_view(),
         name='ledger-create'),
    path('ledger/<slug:entity_slug>/<uuid:ledger_pk>/update/',
         views.LedgerModelUpdateView.as_view(),
         name='ledger-update'),
    path('ledger/<slug:entity_slug>/<uuid:ledger_pk>/balance-sheet/',
         views.LedgerBalanceSheetView.as_view(),
         name='ledger-bs'),
    path('ledger/<slug:entity_slug>/<uuid:ledger_pk>/income-statement/',
         views.LedgerIncomeStatementView.as_view(),
         name='ledger-ic'),

    # Journal Entry Views ----
    path('journal-entry/<slug:entity_slug>/<uuid:ledger_pk>/',
         views.JournalEntryListView.as_view(),
         name='je-list'),
    path('journal-entry/<slug:entity_slug>/<uuid:ledger_pk>/create/',
         views.JournalEntryCreateView.as_view(),
         name='je-create'),
    path('journal-entry/<slug:entity_slug>/<uuid:ledger_pk>/<uuid:je_pk>/',
         views.JournalEntryDetailView.as_view(),
         name='je-detail'),
    path('journal-entry/<slug:entity_slug>/<uuid:ledger_pk>/<uuid:je_pk>/update/',
         views.JournalEntryUpdateView.as_view(),
         name='je-update'),

    # TXS ----
    path('txs/<slug:entity_slug>/<uuid:ledger_pk>/journal-entry/<uuid:je_pk>/',
         views.TXSJournalEntryView.as_view(),
         name='txs-journal-entry'),
    path('txs/<slug:entity_slug>/<slug:coa_slug>/account/<uuid:account_pk>/',
         views.TXSAccountView.as_view(),
         name='txs-account'),

    # INVOICES ----
    path('invoice/<slug:entity_slug>/',
         views.InvoiceModelListView.as_view(),
         name='invoice-list'),
    path('invoice/<slug:entity_slug>/create/',
         views.InvoiceModelCreateView.as_view(),
         name='invoice-create'),
    path('invoice/<slug:entity_slug>/<uuid:invoice_pk>/update/',
         views.InvoiceModelUpdateView.as_view(),
         name='invoice-update'),
    path('invoice/<slug:entity_slug>/<uuid:invoice_pk>/delete/',
         views.InvoiceModelDeleteView.as_view(),
         name='invoice-delete'),
    path('invoice/<slug:entity_slug>/<uuid:invoice_pk>/mark-as-paid/',
         views.InvoiceModelMarkPaidView.as_view(),
         name='invoice-mark-paid'),

    # Bills ----
    path('bill/<slug:entity_slug>/',
         views.BillModelListView.as_view(),
         name='bill-list'),
    path('bill/<slug:entity_slug>/create/',
         views.BillModelCreateView.as_view(),
         name='bill-create'),
    path('bill/<slug:entity_slug>/<uuid:bill_pk>/update/',
         views.BillModelUpdateView.as_view(),
         name='bill-update'),
    path('bill/<slug:entity_slug>/<uuid:bill_pk>/delete/',
         views.BillModelDeleteView.as_view(),
         name='bill-delete'),
    path('bill/<slug:entity_slug>/<uuid:bill_pk>/mark-as-paid/',
         views.BillModelMarkPaidView.as_view(),
         name='bill-mark-paid'),

    # Bank Accounts ---
    path('bank-accounts/<slug:entity_slug>/',
         views.BankAccountModelListView.as_view(),
         name='bank-account-list'),
    path('bank-accounts/<slug:entity_slug>/create/',
         views.BankAccountModelCreateView.as_view(),
         name='bank-account-create'),
    path('bank-accounts/<slug:entity_slug>/<uuid:bank_account_pk>/update/',
         views.BankAccountModelUpdateView.as_view(),
         name='bank-account-update'),

    # Import Data ---
    path('data-import/<slug:entity_slug>/jobs/',
         views.DataImportJobsListView.as_view(),
         name='data-import-jobs-list'),
    path('data-import/<slug:entity_slug>/import-ofx/',
         views.DataImportOFXFileView.as_view(),
         name='data-import-ofx'),
    path('data-import/<slug:entity_slug>/jobs/<uuid:job_pk>/txs/',
         views.DataImportJobDetailView.as_view(),
         name='data-import-job-txs'),

    # Dashboard ----
    path('home/', views.HomeView.as_view(), name='home'),

    # Auth Views ---
    path('accounts/login/', views.DjangoLedgerLoginView.as_view(), name='login'),
    path('accounts/logout/', views.DjangoLedgerLogoutView.as_view(), name='logout'),

    path('', views.RootUrlView.as_view(), name='root-url'),

]
