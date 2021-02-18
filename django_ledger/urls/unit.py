from django.urls import path

from django_ledger.views.unit import (EntityUnitModelListView, EntityUnitModelCreateView,
                                      EntityUnitUpdateView, EntityUnitModelDetailView)

urlpatterns = [
    path('<slug:entity_slug>/unit/list/',
         EntityUnitModelListView.as_view(),
         name='unit-list'),
    path('<slug:entity_slug>/unit/create/',
         EntityUnitModelCreateView.as_view(),
         name='unit-create'),
    path('<slug:entity_slug>/unit/detail/<slug:unit_slug>/',
         EntityUnitModelDetailView.as_view(),
         name='unit-detail'),
    path('<slug:entity_slug>/unit/update/<slug:unit_slug>/',
         EntityUnitUpdateView.as_view(),
         name='unit-update'),
]
