from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/list/',
         views.ChartOfAccountModelListView.as_view(),
         name='coa-list'),
    path('<slug:entity_slug>/detail/<slug:coa_slug>/',
         views.ChartOfAccountModelListView.as_view(),
         name='coa-detail'),
    path('<slug:entity_slug>/update/<slug:coa_slug>/',
         views.ChartOfAccountModelUpdateView.as_view(),
         name='coa-update'),

    # ACTIONS....
    path('<slug:entity_slug>/action/<slug:coa_slug>/mark-as-default/',
         views.CharOfAccountModelActionView.as_view(action_name='mark_as_default'),
         name='coa-action-mark-as-default'),
    path('<slug:entity_slug>/action/<slug:coa_slug>/mark-as-active/',
         views.CharOfAccountModelActionView.as_view(action_name='mark_as_active'),
         name='coa-action-mark-as-active'),
    path('<slug:entity_slug>/action/<slug:coa_slug>/mark-as-inactive/',
         views.CharOfAccountModelActionView.as_view(action_name='mark_as_inactive'),
         name='coa-action-mark-as-inactive'),

]
