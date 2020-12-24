from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/lastest/',
         views.InvoiceModelListView.as_view(),
         name='invoice-list'),
    path('<slug:entity_slug>/year/<int:year>/',
         views.InvoiceModelYearlyListView.as_view(),
         name='invoice-list-year'),
    path('<slug:entity_slug>/month/<int:year>/<int:month>/',
         views.InvoiceModelMonthlyListView.as_view(),
         name='invoice-list-month'),
    path('<slug:entity_slug>/create/',
         views.InvoiceModelCreateView.as_view(),
         name='invoice-create'),
    path('<slug:entity_slug>/detail/<uuid:invoice_pk>/',
         views.InvoiceModelDetailView.as_view(),
         name='invoice-detail'),
    path('<slug:entity_slug>/update/<uuid:invoice_pk>/',
         views.InvoiceModelUpdateView.as_view(),
         name='invoice-update'),
    path('<slug:entity_slug>/delete/<uuid:invoice_pk>/',
         views.InvoiceModelDeleteView.as_view(),
         name='invoice-delete'),
    path('<slug:entity_slug>/mark-as-paid/<uuid:invoice_pk>/',
         views.InvoiceModelMarkPaidView.as_view(),
         name='invoice-mark-paid'),

]
