from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/',
         views.BillModelListView.as_view(),
         name='bill-list'),
    path('<slug:entity_slug>/create/',
         views.BillModelCreateView.as_view(),
         name='bill-create'),
    path('<slug:entity_slug>/<uuid:bill_pk>/detail/',
         views.BillModelDetailView.as_view(),
         name='bill-detail'),
    path('<slug:entity_slug>/<uuid:bill_pk>/update/',
         views.BillModelUpdateView.as_view(),
         name='bill-update'),
    path('<slug:entity_slug>/<uuid:bill_pk>/delete/',
         views.BillModelDeleteView.as_view(),
         name='bill-delete'),
    path('<slug:entity_slug>/<uuid:bill_pk>/mark-as-paid/',
         views.BillModelMarkPaidView.as_view(),
         name='bill-mark-paid'),
]
