from django.urls import path

from django_ledger.views import (
    ProductListView, ProductCreateView, UnitOfMeasureModelCreateView,
    UnitOfMeasureModelListView, UnitOfMeasureModelUpdateView, ProductUpdateView,
    ExpenseItemCreateView, ExpenseItemModelListView, ExpenseItemUpdateView, InventoryItemModelListView,
    InventoryItemCreateView, InventoryItemUpdateView, UnitOfMeasureModelDeleteView, ProductDeleteView,
    ServiceListView, ServiceCreateView, ServiceUpdateView, ServiceDeleteView
)

urlpatterns = [

    # Unit of Measure Views...
    path('<str:entity_slug>/uom/list/', UnitOfMeasureModelListView.as_view(), name='uom-list'),
    path('<str:entity_slug>/uom/create/', UnitOfMeasureModelCreateView.as_view(), name='uom-create'),
    path('<str:entity_slug>/uom/update/<uuid:uom_pk>/', UnitOfMeasureModelUpdateView.as_view(), name='uom-update'),
    path('<str:entity_slug>/uom/delete/<uuid:uom_pk>/', UnitOfMeasureModelDeleteView.as_view(), name='uom-delete'),

    # Product Views....
    path('<str:entity_slug>/product/list/', ProductListView.as_view(), name='product-list'),
    path('<str:entity_slug>/product/create/', ProductCreateView.as_view(), name='product-create'),
    path('<str:entity_slug>/product/update/<uuid:item_pk>/', ProductUpdateView.as_view(), name='product-update'),
    path('<str:entity_slug>/product/delete/<uuid:item_pk>/', ProductDeleteView.as_view(), name='product-delete'),

    # Service Views...
    path('<str:entity_slug>/service/list', ServiceListView.as_view(), name='service-list'),
    path('<str:entity_slug>/service/create/', ServiceCreateView.as_view(), name='service-create'),
    path('<str:entity_slug>/service/update/<uuid:item_pk>/', ServiceUpdateView.as_view(), name='service-update'),
    path('<str:entity_slug>/service/delete/<uuid:item_pk>/', ServiceDeleteView.as_view(), name='service-delete'),

    # Expense Views...
    path('<str:entity_slug>/expense/list/', ExpenseItemModelListView.as_view(), name='expense-list'),
    path('<str:entity_slug>/expense/create/', ExpenseItemCreateView.as_view(), name='expense-create'),
    path('<str:entity_slug>/expense/update/<uuid:item_pk>/', ExpenseItemUpdateView.as_view(), name='expense-update'),

    # Inventory Views...
    path('<str:entity_slug>/list/inventory/', InventoryItemModelListView.as_view(), name='inventory-item-list'),
    path('<str:entity_slug>/create/inventory/', InventoryItemCreateView.as_view(), name='inventory-item-create'),
    path('<str:entity_slug>/update/inventory/<uuid:item_pk>/', InventoryItemUpdateView.as_view(),
         name='inventory-item-update'),

]
