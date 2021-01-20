from django.urls import path

from django_ledger.views import (
    ProductsAndServicesListView, ProductOrServiceCreateView, UnitOfMeasureModelCreateView,
    UnitOfMeasureModelListView, UnitOfMeasureModelUpdateView, ProductOrServiceUpdateView,
    ExpenseItemCreateView, ExpenseItemModelListView, ExpenseItemUpdateView)

urlpatterns = [
    path('<str:entity_slug>/list/uom/', UnitOfMeasureModelListView.as_view(), name='uom-list'),
    path('<str:entity_slug>/create/uom/', UnitOfMeasureModelCreateView.as_view(), name='uom-create'),
    path('<str:entity_slug>/update/uom/<uuid:uom_pk>/', UnitOfMeasureModelUpdateView.as_view(), name='uom-update'),

    path('<str:entity_slug>/list/product/', ProductsAndServicesListView.as_view(), name='product-list'),
    path('<str:entity_slug>/create/product/', ProductOrServiceCreateView.as_view(), name='product-create'),
    path('<str:entity_slug>/update/product/<uuid:item_pk>/',
         ProductOrServiceUpdateView.as_view(),
         name='product-update'),

    path('<str:entity_slug>/list/expense/', ExpenseItemModelListView.as_view(), name='expense-list'),
    path('<str:entity_slug>/create/expense/', ExpenseItemCreateView.as_view(), name='expense-create'),
    path('<str:entity_slug>/update/expense/<uuid:item_pk>/',
         ExpenseItemUpdateView.as_view(),
         name='expense-update'),

]
