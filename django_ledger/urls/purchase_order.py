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
    path('<slug:entity_slug>/detail/<uuid:po_pk>/',
         views.PurchaseOrderModelDetailView.as_view(),
         name='po-detail'),
    path('<slug:entity_slug>/update/<uuid:po_pk>/',
         views.PurchaseOrderModelUpdateView.as_view(),
         name='po-update'),
    path('<slug:entity_slug>/update/<uuid:po_pk>/update-items/',
         views.PurchaseOrderModelUpdateView.as_view(update_items=True),
         name='po-update-items'),
    path('<slug:entity_slug>/delete/<uuid:po_pk>/',
         views.PurchaseOrderModelDeleteView.as_view(),
         name='po-delete'),
    # path('<slug:entity_slug>/mark-as-paid/<uuid:bill_pk>/',
    #      views.BillModelMarkPaidView.as_view(),
    #      name='bill-mark-paid'),
]
