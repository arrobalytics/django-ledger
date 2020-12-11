from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/data/pnl/',
         views.EntityProfitNLossAPIView.as_view(),
         name='entity-json-pnl'),
    path('<slug:entity_slug>/data/net-payables/',
         views.EntityPayableNetAPIView.as_view(),
         name='entity-json-net-payables'),
    path('<slug:entity_slug>/data/net-receivables/',
         views.EntityReceivableNetAPIView.as_view(),
         name='entity-json-net-receivables'),
]
