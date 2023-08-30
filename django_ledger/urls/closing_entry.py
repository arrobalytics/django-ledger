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

    # ACTIONS...
    path('<slug:entity_slug>/action/<uuid:closing_entry_pk>/post/',
         views.ClosingEntryModelActionMarkAsPostedView.as_view(),
         name='closing-entry-action-mark-as-posted'),
    path('<slug:entity_slug>/action/<uuid:closing_entry_pk>/unpost/',
         views.ClosingEntryModelActionMarkAsUnPostedView.as_view(),
         name='closing-entry-action-mark-as-unposted'),

]
