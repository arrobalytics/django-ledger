from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/<uuid:ledger_pk>/journal-entry/<uuid:je_pk>/',
         views.TXSJournalEntryView.as_view(),
         name='txs-journal-entry'),
    path('<slug:entity_slug>/<slug:coa_slug>/account/<uuid:account_pk>/',
         views.TXSAccountView.as_view(),
         name='txs-account'),
]
