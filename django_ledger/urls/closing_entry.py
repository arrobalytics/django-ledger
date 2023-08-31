from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/latest/',
         views.ClosingEntryModelListView.as_view(),
         name='closing-entry-list'),
    path('<slug:entity_slug>/list/year/<int:year>/',
         views.ClosingEntryModelYearListView.as_view(),
         name='closing-entry-list-year'),
    path('<slug:entity_slug>/list/month/<int:year>/<int:month>/',
         views.ClosingEntryModelMonthListView.as_view(),
         name='closing-entry-list-month'),
    path('<slug:entity_slug>/create/',
         views.ClosingEntryModelCreateView.as_view(),
         name='closing-entry-create'),
    path('<slug:entity_slug>/detail/<uuid:closing_entry_pk>/',
         views.ClosingEntryModelDetailView.as_view(),
         name='closing-entry-detail'),
    path('<slug:entity_slug>/delete/<uuid:closing_entry_pk>/',
         views.ClosingEntryDeleteView.as_view(),
         name='closing-entry-delete'),

    # ACTIONS...
    path('<slug:entity_slug>/action/<uuid:closing_entry_pk>/post/',
         views.ClosingEntryModelActionView.as_view(action_name='mark_as_posted'),
         name='closing-entry-action-mark-as-posted'),
    path('<slug:entity_slug>/action/<uuid:closing_entry_pk>/unpost/',
         views.ClosingEntryModelActionView.as_view(action_name='mark_as_unposted'),
         name='closing-entry-action-mark-as-unposted'),
    path('<slug:entity_slug>/action/<uuid:closing_entry_pk>/update-txs/',
         views.ClosingEntryModelActionView.as_view(action_name='update_transactions'),
         name='closing-entry-action-update-txs'),

]
