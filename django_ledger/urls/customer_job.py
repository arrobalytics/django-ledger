from django.urls import path
from django_ledger.views import CustomerJobModelListView, CustomerJobModelCreateView

urlpatterns = [
    path('<slug:entity_slug>/list/', CustomerJobModelListView.as_view(), name='customer-job-list'),
    path('<slug:entity_slug>/create/', CustomerJobModelCreateView.as_view(), name='customer-job-create'),
]