from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/data/pnl/',
         views.EntityPnLDataView.as_view(),
         name='entity-json-pnl'),
    path('<slug:entity_slug>/data/net-payables/',
         views.EntityPayableNetDataView.as_view(),
         name='entity-json-net-payables'),
    path('<slug:entity_slug>/data/net-receivables/',
         views.EntityReceivableNetDataView.as_view(),
         name='entity-json-net-receivables'),
]
