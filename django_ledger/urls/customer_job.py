from django.urls import path
from django_ledger.views import CustomerJobModelListView, CustomerJobModelCreateView, CustomerJobModelDetailView

urlpatterns = [
    path('<slug:entity_slug>/list/', CustomerJobModelListView.as_view(), name='customer-job-list'),
    path('<slug:entity_slug>/create/', CustomerJobModelCreateView.as_view(), name='customer-job-create'),
    path('<slug:entity_slug>/detail/<uuid:customer_job_pk>/', CustomerJobModelDetailView.as_view(), name='customer-job-detail'),
]