from django.urls import path
from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/list/', views.LedgerModelListView.as_view(), name='ledger-list'),
    path('<slug:entity_slug>/list/hidden/', views.LedgerModelListView.as_view(show_hidden=True),
         name='ledger-list-hidden'),
    path('<slug:entity_slug>/create/', views.LedgerModelCreateView.as_view(), name='ledger-create'),
    path('<slug:entity_slug>/update/<uuid:ledger_pk>/', views.LedgerModelUpdateView.as_view(), name='ledger-update'),
    path('<slug:entity_slug>/delete/<uuid:ledger_pk>/', views.LedgerModelDeleteView.as_view(), name='ledger-delete'),

    # ACTIONS...
    path('<slug:entity_slug>/action/<uuid:ledger_pk>/post/',
         views.LedgerModelModelActionView.as_view(action_name='post'),
         name='ledger-action-post'),
    path('<slug:entity_slug>/action/<uuid:ledger_pk>/unpost/',
         views.LedgerModelModelActionView.as_view(action_name='unpost'),
         name='ledger-action-unpost'),
    path('<slug:entity_slug>/action/<uuid:ledger_pk>/lock/',
         views.LedgerModelModelActionView.as_view(action_name='lock'),
         name='ledger-action-lock'),
    path('<slug:entity_slug>/action/<uuid:ledger_pk>/unlock/',
         views.LedgerModelModelActionView.as_view(action_name='unlock'),
         name='ledger-action-unlock'),

]
