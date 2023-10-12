from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/jobs/',
         views.ImportJobModelListView.as_view(),
         name='data-import-jobs-list'),
    path('<slug:entity_slug>/jobs/<uuid:job_pk>/update/',
         views.ImportJobModelUpdateView.as_view(),
         name='data-import-jobs-update'),
    path('<slug:entity_slug>/jobs/<uuid:job_pk>/delete/',
         views.ImportJobModelDeleteView.as_view(),
         name='data-import-jobs-delete'),
    path('<slug:entity_slug>/import-ofx/',
         views.ImportJobModelCreateView.as_view(),
         name='data-import-ofx'),
    path('<slug:entity_slug>/jobs/<uuid:job_pk>/txs/',
         views.DataImportJobDetailView.as_view(),
         name='data-import-job-txs'),
]
