from django.urls import path
from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/', views.VendorModelListView.as_view(), name='vendor-list'),
    path('<slug:entity_slug>/create/', views.VendorModelCreateView.as_view(), name='vendor-create'),
    path('<slug:entity_slug>/update/<uuid:vendor_pk>/', views.VendorModelUpdateView.as_view(), name='vendor-update'),

]