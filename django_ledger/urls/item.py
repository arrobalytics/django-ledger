from django.urls import path

from django_ledger.views import (
    ItemModelListViewList, ProductOrServiceCreateView, UnitOfMeasureModelCreateView,
    UnitOfMeasureModelListView, UnitOfMeasureModelUpdateView, ProductOrServiceUpdateView)

urlpatterns = [
    path('<str:entity_slug>/list/items/', ItemModelListViewList.as_view(), name='item-list'),
    path('<str:entity_slug>/list/uom/', UnitOfMeasureModelListView.as_view(), name='uom-list'),

    path('<str:entity_slug>/create/product/', ProductOrServiceCreateView.as_view(), name='product-create'),
    path('<str:entity_slug>/create/uom/', UnitOfMeasureModelCreateView.as_view(), name='uom-create'),

    path('<str:entity_slug>/update/product/<uuid:item_pk>/', ProductOrServiceUpdateView.as_view(), name='product-update'),
    path('<str:entity_slug>/update/uom/<uuid:uom_pk>/', UnitOfMeasureModelUpdateView.as_view(), name='uom-update'),

]
