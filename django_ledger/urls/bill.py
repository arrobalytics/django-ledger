from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/list/',
         views.BillModelListView.as_view(),
         name='bill-list'),
    path('<slug:entity_slug>/list/<int:year>/',
         views.BillModelYearListView.as_view(),
         name='bill-list-year'),
    path('<slug:entity_slug>/list/<int:year>/<int:month>/',
         views.BillModelMonthListView.as_view(),
         name='bill-list-month'),
    path('<slug:entity_slug>/create/',
         views.BillModelCreateView.as_view(),
         name='bill-create'),
    path('<slug:entity_slug>/detail/<uuid:bill_pk>/',
         views.BillModelDetailView.as_view(),
         name='bill-detail'),
    path('<slug:entity_slug>/update/<uuid:bill_pk>/',
         views.BillModelUpdateView.as_view(),
         name='bill-update'),
    path('<slug:entity_slug>/delete/<uuid:bill_pk>/',
         views.BillModelDeleteView.as_view(),
         name='bill-delete'),
    path('<slug:entity_slug>/mark-as-paid/<uuid:bill_pk>/',
         views.BillModelMarkPaidView.as_view(),
         name='bill-mark-paid'),
]
