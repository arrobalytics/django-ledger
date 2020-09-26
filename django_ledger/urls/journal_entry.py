from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/<uuid:ledger_pk>/',
         views.JournalEntryListView.as_view(),
         name='je-list'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/create/',
         views.JournalEntryCreateView.as_view(),
         name='je-create'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/<uuid:je_pk>/',
         views.JournalEntryDetailView.as_view(),
         name='je-detail'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/<uuid:je_pk>/update/',
         views.JournalEntryUpdateView.as_view(),
         name='je-update'),
]
