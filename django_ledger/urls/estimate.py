from django.urls import path

from django_ledger.views import (EstimateModelListView, EstimateModelCreateView,
                                 EstimateModelDetailView, EstimateModelUpdateView,
                                 EstimateActionMarkAsDraftView, EstimateActionMarkAsReviewView,
                                 EstimateActionMarkAsApprovedView, EstimateActionMarkAsCompletedView,
                                 EstimateActionMarkAsCanceledView)

urlpatterns = [
    path('<slug:entity_slug>/list/', EstimateModelListView.as_view(), name='customer-estimate-list'),
    path('<slug:entity_slug>/create/', EstimateModelCreateView.as_view(), name='customer-estimate-create'),
    path('<slug:entity_slug>/detail/<uuid:ce_pk>/',
         EstimateModelDetailView.as_view(),
         name='customer-estimate-detail'),
    path('<slug:entity_slug>/update/<uuid:ce_pk>/',
         EstimateModelUpdateView.as_view(),
         name='customer-estimate-update'),
    path('<slug:entity_slug>/update/<uuid:ce_pk>/items/',
         EstimateModelUpdateView.as_view(action_update_items=True),
         name='customer-estimate-update-items'),

    # Actions....
    path('<slug:entity_slug>/action/<uuid:ce_pk>/mark-as-draft/',
         EstimateActionMarkAsDraftView.as_view(),
         name='customer-estimate-action-mark-as-draft'),
    path('<slug:entity_slug>/action/<uuid:ce_pk>/mark-as-review/',
         EstimateActionMarkAsReviewView.as_view(),
         name='customer-estimate-action-mark-as-review'),
    path('<slug:entity_slug>/action/<uuid:ce_pk>/mark-as-approved/',
         EstimateActionMarkAsApprovedView.as_view(),
         name='customer-estimate-action-mark-as-approved'),
    path('<slug:entity_slug>/action/<uuid:ce_pk>/mark-as-completed/',
         EstimateActionMarkAsCompletedView.as_view(),
         name='customer-estimate-action-mark-as-completed'),
    path('<slug:entity_slug>/action/<uuid:ce_pk>/mark-as-canceled/',
         EstimateActionMarkAsCanceledView.as_view(),
         name='customer-estimate-action-mark-as-canceled'),
]
