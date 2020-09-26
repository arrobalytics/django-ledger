from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/jobs/',
         views.DataImportJobsListView.as_view(),
         name='data-import-jobs-list'),
    path('<slug:entity_slug>/import-ofx/',
         views.DataImportOFXFileView.as_view(),
         name='data-import-ofx'),
    path('<slug:entity_slug>/jobs/<uuid:job_pk>/txs/',
         views.DataImportJobDetailView.as_view(),
         name='data-import-job-txs'),
]
