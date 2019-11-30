from django.urls import path

from . import views

app_name = 'django_ledger'

urlpatterns = [
    path('entity/', views.EntityModelListView.as_view(), name='entity-list'),
    path('entity/<slug:entity_slug>/', views.EntityModelDetailVew.as_view(), name='entity-detail'),

    path('coa/<slug:coa_slug>', views.ChartOfAccountsDetailView.as_view(), name='coa-detail'),

    path('entity/<slug:entity_slug>/balance-sheet/', views.EntityModelDetailVew.as_view(), name='entity-bs'),
    path('entity/<slug:entity_slug>/income-statement/', views.EntityModelDetailVew.as_view(), name='entity-ic'),
]
