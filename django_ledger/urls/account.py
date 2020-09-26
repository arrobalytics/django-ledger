from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/<slug:coa_slug>/',
         views.AccountModelListView.as_view(),
         name='account-list'),
    path('<slug:entity_slug>/<slug:coa_slug>/create/',
         views.AccountModelCreateView.as_view(),
         name='account-create'),
    path('<slug:entity_slug>/<slug:coa_slug>/<uuid:account_pk>/update/',
         views.AccountModelUpdateView.as_view(),
         name='account-update'), ]
