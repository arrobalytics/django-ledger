from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/',
         views.InvoiceModelListView.as_view(),
         name='invoice-list'),
    path('<slug:entity_slug>/create/',
         views.InvoiceModelCreateView.as_view(),
         name='invoice-create'),
    path('<slug:entity_slug>/<uuid:invoice_pk>/update/',
         views.InvoiceModelUpdateView.as_view(),
         name='invoice-update'),
    path('<slug:entity_slug>/<uuid:invoice_pk>/delete/',
         views.InvoiceModelDeleteView.as_view(),
         name='invoice-delete'),
    path('<slug:entity_slug>/<uuid:invoice_pk>/mark-as-paid/',
         views.InvoiceModelMarkPaidView.as_view(),
         name='invoice-mark-paid'),

]
