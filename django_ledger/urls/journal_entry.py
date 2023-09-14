from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/<uuid:ledger_pk>/list/',
         views.JournalEntryListView.as_view(),
         name='je-list'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/list/year/<int:year>/',
         views.JournalEntryYearListView.as_view(),
         name='je-list-year'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/list/month/<int:year>/<int:month>/',
         views.JournalEntryMonthListView.as_view(),
         name='je-list-month'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/create/',
         views.JournalEntryCreateView.as_view(),
         name='je-create'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/detail/<uuid:je_pk>/',
         views.JournalEntryDetailView.as_view(),
         name='je-detail'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/detail/<uuid:je_pk>/txs/',
         views.JournalEntryModelTXSDetailView.as_view(),
         name='je-detail-txs'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/update/<uuid:je_pk>/',
         views.JournalEntryUpdateView.as_view(),
         name='je-update'),

    # actions...
    path('<slug:entity_slug>/<uuid:ledger_pk>/update/<uuid:je_pk>/mark-as-posted/',
         views.JournalEntryActionMarkAsPostedView.as_view(),
         name='je-mark-as-posted'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/update/<uuid:je_pk>/mark-as-unposted/',
         views.JournalEntryActionMarkAsUnPostedView.as_view(),
         name='je-mark-as-unposted'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/update/<uuid:je_pk>/mark-as-locked/',
         views.JournalEntryActionMarkAsLockedView.as_view(),
         name='je-mark-as-locked'),
    path('<slug:entity_slug>/<uuid:ledger_pk>/update/<uuid:je_pk>/mark-as-unlocked/',
         views.JournalEntryActionMarkAsUnLockedView.as_view(),
         name='je-mark-as-unlocked'),
]
