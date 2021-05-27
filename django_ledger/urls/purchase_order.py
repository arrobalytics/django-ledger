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
    # path('<slug:entity_slug>/update/<uuid:bill_pk>/',
    #      views.BillModelUpdateView.as_view(),
    #      name='bill-update'),
    # path('<slug:entity_slug>/update/<uuid:bill_pk>/items/',
    #      views.BillModelItemsUpdateView.as_view(),
    #      name='bill-update-items'),
    # path('<slug:entity_slug>/delete/<uuid:bill_pk>/',
    #      views.BillModelDeleteView.as_view(),
    #      name='bill-delete'),
    # path('<slug:entity_slug>/mark-as-paid/<uuid:bill_pk>/',
    #      views.BillModelMarkPaidView.as_view(),
    #      name='bill-mark-paid'),
]
