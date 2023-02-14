from django.urls import path

from django_ledger.views import (
    ProductListView, ProductCreateView, UnitOfMeasureModelCreateView,
    UnitOfMeasureModelListView, UnitOfMeasureModelUpdateView, ProductUpdateView,
    ExpenseItemCreateView, ExpenseItemModelListView, ExpenseItemUpdateView, InventoryItemModelListView,
    InventoryItemCreateView, InventoryItemUpdateView, UnitOfMeasureModelDeleteView, ProductDeleteView)

urlpatterns = [
    path('<str:entity_slug>/list/uom/', UnitOfMeasureModelListView.as_view(), name='uom-list'),
    path('<str:entity_slug>/create/uom/', UnitOfMeasureModelCreateView.as_view(), name='uom-create'),
    path('<str:entity_slug>/update/uom/<uuid:uom_pk>/', UnitOfMeasureModelUpdateView.as_view(), name='uom-update'),
    path('<str:entity_slug>/delete/uom/<uuid:uom_pk>/', UnitOfMeasureModelDeleteView.as_view(), name='uom-delete'),

    path('<str:entity_slug>/list/product/', ProductListView.as_view(), name='product-list'),
    path('<str:entity_slug>/create/product/', ProductCreateView.as_view(), name='product-create'),
    path('<str:entity_slug>/update/product/<uuid:item_pk>/', ProductUpdateView.as_view(),
         name='product-update'),
    path('<str:entity_slug>/delete/product/<uuid:item_pk>/', ProductDeleteView.as_view(),
         name='product-delete'),

    path('<str:entity_slug>/list/expense/', ExpenseItemModelListView.as_view(), name='expense-list'),
    path('<str:entity_slug>/create/expense/', ExpenseItemCreateView.as_view(), name='expense-create'),
    path('<str:entity_slug>/update/expense/<uuid:item_pk>/',
         ExpenseItemUpdateView.as_view(),
         name='expense-update'),

    path('<str:entity_slug>/list/inventory/', InventoryItemModelListView.as_view(), name='inventory-item-list'),
    path('<str:entity_slug>/create/inventory/', InventoryItemCreateView.as_view(), name='inventory-item-create'),
    path('<str:entity_slug>/update/inventory/<uuid:item_pk>/',
         InventoryItemUpdateView.as_view(),
         name='inventory-item-update'),

]
