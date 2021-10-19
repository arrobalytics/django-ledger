from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/latest/',
         views.BillModelListView.as_view(),
         name='bill-list'),
    path('<slug:entity_slug>/year/<int:year>/',
         views.BillModelYearListView.as_view(),
         name='bill-list-year'),
    path('<slug:entity_slug>/month/<int:year>/<int:month>/',
         views.BillModelMonthListView.as_view(),
         name='bill-list-month'),
    path('<slug:entity_slug>/create/',
         views.BillModelCreateView.as_view(),
         name='bill-create'),
    path('<slug:entity_slug>/create/purchase-order/<uuid:po_pk>/',
         views.BillModelCreateView.as_view(for_purchase_order=True),
         name='bill-create-po'),
    path('<slug:entity_slug>/detail/<uuid:bill_pk>/',
         views.BillModelDetailView.as_view(),
         name='bill-detail'),
    path('<slug:entity_slug>/update/<uuid:bill_pk>/',
         views.BillModelUpdateView.as_view(),
         name='bill-update'),
    path('<slug:entity_slug>/update/<uuid:bill_pk>/items/',
         views.BillModelUpdateView.as_view(action_update_items=True),
         name='bill-update-items'),
    path('<slug:entity_slug>/delete/<uuid:bill_pk>/',
         views.BillModelDeleteView.as_view(),
         name='bill-delete'),
    path('<slug:entity_slug>/mark-as-paid/<uuid:bill_pk>/',
         views.BillModelMarkPaidView.as_view(),
         name='bill-mark-paid'),
    path('<slug:entity_slug>/void/<uuid:bill_pk>/',
         views.BillModelDeleteView.as_view(void=True),
         name='bill-void'),

    # actions....
    path('<slug:entity_slug>/actions/<uuid:bill_pk>/force-migrate/',
         views.BillModelActionView.as_view(
             action=views.BillModelActionView.ACTION_FORCE_MIGRATE),
         name='bill-action-force-migrate'),
    path('<slug:entity_slug>/actions/<uuid:bill_pk>/lock/',
         views.BillModelActionView.as_view(
             action=views.BillModelActionView.ACTION_LOCK),
         name='bill-action-lock'),
    path('<slug:entity_slug>/actions/<uuid:bill_pk>/unlock/',
         views.BillModelActionView.as_view(
             action=views.BillModelActionView.ACTION_UNLOCK),
         name='bill-action-unlock'),
]
