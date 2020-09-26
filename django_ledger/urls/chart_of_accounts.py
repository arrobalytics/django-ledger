from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/<slug:coa_slug>/update/', views.ChartOfAccountsUpdateView.as_view(), name='coa-update'),
]
