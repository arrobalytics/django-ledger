from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/latest/',
         views.PurchaseOrderModelListView.as_view(),
         name='po-list'),
    path('<slug:entity_slug>/year/<int:year>/',
         views.PurchaseOrderModelYearListView.as_view(),
         name='po-list-year'),
    path('<slug:entity_slug>/month/<int:year>/<int:month>/',
         views.PurchaseOrderModelMonthListView.as_view(),
         name='po-list-month'),

    path('<slug:entity_slug>/create/',
         views.PurchaseOrderModelCreateView.as_view(),
         name='po-create'),
    path('<slug:entity_slug>/create/estimate/<uuid:ce_pk>/',
         views.PurchaseOrderModelCreateView.as_view(for_estimate=True),
         name='po-create-estimate'),

    path('<slug:entity_slug>/detail/<uuid:po_pk>/',
         views.PurchaseOrderModelDetailView.as_view(),
         name='po-detail'),
    path('<slug:entity_slug>/update/<uuid:po_pk>/',
         views.PurchaseOrderModelUpdateView.as_view(),
         name='po-update'),
    path('<slug:entity_slug>/update/<uuid:po_pk>/update-items/',
         views.PurchaseOrderModelUpdateView.as_view(update_items=True),
         name='po-update-items'),
    # path('<slug:entity_slug>/update/<uuid:po_pk>/mark-as-fulfilled/',
    #      views.PurchaseOrderModelUpdateView.as_view(mark_as_fulfilled=True),
    #      name='po-mark-as-fulfilled'),
    path('<slug:entity_slug>/delete/<uuid:po_pk>/',
         views.PurchaseOrderModelDeleteView.as_view(),
         name='po-delete'),

    # Actions....
    path('<slug:entity_slug>/action/<uuid:po_pk>/mark-as-draft/',
         views.PurchaseOrderMarkAsDraftView.as_view(),
         name='po-action-mark-as-draft'),
    path('<slug:entity_slug>/action/<uuid:po_pk>/mark-as-review/',
         views.PurchaseOrderMarkAsReviewView.as_view(),
         name='po-action-mark-as-review'),
    path('<slug:entity_slug>/action/<uuid:po_pk>/mark-as-approved/',
         views.PurchaseOrderMarkAsApprovedView.as_view(),
         name='po-action-mark-as-approved'),
    path('<slug:entity_slug>/action/<uuid:po_pk>/mark-as-fulfilled/',
         views.PurchaseOrderMarkAsFulfilledView.as_view(),
         name='po-action-mark-as-fulfilled'),
    path('<slug:entity_slug>/action/<uuid:po_pk>/mark-as-canceled/',
         views.PurchaseOrderMarkAsCanceledView.as_view(),
         name='po-action-mark-as-canceled'),

]
