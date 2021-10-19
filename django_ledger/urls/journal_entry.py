from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/<uuid:ledger_pk>/list/',
         views.JournalEntryListView.as_view(),
         name='je-list'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/create/',
         views.JournalEntryCreateView.as_view(),
         name='je-create'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/detail/<uuid:je_pk>/',
         views.JournalEntryDetailView.as_view(),
         name='je-detail'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/update/<uuid:je_pk>/',
         views.JournalEntryUpdateView.as_view(),
         name='je-update'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/update/<uuid:je_pk>/mark-as-posted/',
         views.JournalEntryUpdateView.as_view(action_mark_as_posted=True),
         name='je-mark-as-posted'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/update/<uuid:je_pk>/mark-as-locked/',
         views.JournalEntryUpdateView.as_view(action_mark_as_locked=True),
         name='je-mark-as-locked'),
]
