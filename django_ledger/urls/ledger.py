from django.urls import path
from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/list/', views.LedgerModelListView.as_view(), name='ledger-list'),
    path('<slug:entity_slug>/create/', views.LedgerModelCreateView.as_view(), name='ledger-create'),
    path('<slug:entity_slug>/update/<uuid:ledger_pk>/', views.LedgerModelUpdateView.as_view(), name='ledger-update'),
]
