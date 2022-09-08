"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.urls import path, include

from django_ledger import views

app_name = 'django_ledger'

urlpatterns = [

    path('entity/', include('django_ledger.urls.entity')),
    path('unit/', include('django_ledger.urls.unit')),
    path('financial-statement/', include('django_ledger.urls.financial_statement')),
    path('chart-of-accounts/', include('django_ledger.urls.chart_of_accounts')),
    path('account/', include('django_ledger.urls.account')),
    path('ledger/', include('django_ledger.urls.ledger')),
    path('journal-entry/', include('django_ledger.urls.journal_entry')),
    path('transactions/', include('django_ledger.urls.transactions')),
    path('invoice/', include('django_ledger.urls.invoice')),
    path('bill/', include('django_ledger.urls.bill')),
    path('purchase_order/', include('django_ledger.urls.purchase_order')),
    path('customer/', include('django_ledger.urls.customer')),
    path('customer-job/', include('django_ledger.urls.estimate')),
    path('vendor/', include('django_ledger.urls.vendor')),
    path('item/', include('django_ledger.urls.item')),
    path('bank-account/', include('django_ledger.urls.bank_account')),
    path('data-import/', include('django_ledger.urls.data_import')),
    path('auth/', include('django_ledger.urls.auth')),
    path('feedback/', include('django_ledger.urls.feedback')),
    path('inventory/', include('django_ledger.urls.inventory')),
    path('home/', include('django_ledger.urls.home')),
    path('djl-api/v1/', include('django_ledger.urls.djl_api')),
    path('', views.RootUrlView.as_view(), name='root'),
]
