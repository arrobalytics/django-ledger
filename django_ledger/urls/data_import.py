from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/jobs/', views.ImportJobModelListView.as_view(), name='import-job-list'),
    path(
        '<slug:entity_slug>/jobs/<uuid:job_pk>/detail/', views.ImportJobDetailView.as_view(), name='import-job-detail'
    ),
    path(
        '<slug:entity_slug>/jobs/<uuid:job_pk>/update/',
        views.ImportJobModelUpdateView.as_view(),
        name='import-job-update',
    ),
    path(
        '<slug:entity_slug>/jobs/<uuid:job_pk>/delete/',
        views.ImportJobModelDeleteView.as_view(),
        name='import-job-delete',
    ),
    path('<slug:entity_slug>/import-ofx/', views.ImportJobModelCreateView.as_view(), name='data-import-ofx'),
    path(
        '<slug:entity_slug>/jobs/<uuid:job_pk>/reset/',
        views.ImportJobModelResetView.as_view(),
        name='data-import-job-txs-undo',
    ),
    path(
        '<slug:entity_slug>/jobs/<uuid:job_pk>/txs/<uuid:staged_tx_pk>/update/',
        views.StagedTransactionUpdateView.as_view(),
        name='data-import-staged-tx-update',
    ),
    path(
        '<slug:entity_slug>/jobs/<uuid:job_pk>/txs/<uuid:staged_tx_pk>/undo/',
        views.StagedTransactionUndoView.as_view(),
        name='data-import-staged-tx-undo',
    ),
    path(
        '<slug:entity_slug>/jobs/<uuid:job_pk>/txs/<uuid:staged_tx_pk>/unmatch/',
        views.StagedTransactionUnmatchView.as_view(),
        name='data-import-staged-tx-unmatch',
    ),
]
