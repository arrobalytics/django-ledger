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
    path('<slug:entity_slug>/update/<uuid:invoice_pk>/items/',
         views.InvoiceModelUpdateView.as_view(action_update_items=True),
         name='invoice-update-items'),
    path('<slug:entity_slug>/delete/<uuid:invoice_pk>/',
         views.InvoiceModelDeleteView.as_view(),
         name='invoice-delete'),
    path('<slug:entity_slug>/mark-as-paid/<uuid:invoice_pk>/',
         views.InvoiceModelMarkPaidView.as_view(),
         name='invoice-mark-paid'),

    # actions....
    path('<slug:entity_slug>/actions/<uuid:invoice_pk>/force-migrate/',
         views.InvoiceModelActionView.as_view(
             action=views.InvoiceModelActionView.ACTION_FORCE_MIGRATE),
         name='invoice-action-force-migrate'),
    path('<slug:entity_slug>/actions/<uuid:invoice_pk>/lock/',
         views.InvoiceModelActionView.as_view(
             action=views.InvoiceModelActionView.ACTION_LOCK),
         name='invoice-action-lock'),
    path('<slug:entity_slug>/actions/<uuid:invoice_pk>/unlock/',
         views.InvoiceModelActionView.as_view(
             action=views.InvoiceModelActionView.ACTION_UNLOCK),
         name='invoice-action-unlock'),

]
