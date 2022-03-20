from django.urls import path
from django_ledger.views import (CustomerJobModelListView, CustomerJobModelCreateView,
                                 CustomerJobModelDetailView, CustomerJobModelUpdateView)

urlpatterns = [
    path('<slug:entity_slug>/list/', CustomerJobModelListView.as_view(), name='customer-job-list'),
    path('<slug:entity_slug>/create/', CustomerJobModelCreateView.as_view(), name='customer-job-create'),
    path('<slug:entity_slug>/detail/<uuid:customer_job_pk>/',
         CustomerJobModelDetailView.as_view(),
         name='customer-job-detail'),
    path('<slug:entity_slug>/update/<uuid:customer_job_pk>/',
         CustomerJobModelUpdateView.as_view(),
         name='customer-job-update'),
]