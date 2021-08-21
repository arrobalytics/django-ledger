from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/list/',
         views.InventoryListView.as_view(),
         name='inventory-list'),
]