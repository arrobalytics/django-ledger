"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

from django.urls import path

from django_ledger import views

urlpatterns = [
    path(
        '<slug:entity_slug>/latest/',
        views.ReceiptModelListView.as_view(),
        name='receipt-list',
    ),
    path(
        '<slug:entity_slug>/year/<int:year>/',
        views.ReceiptModelYearListView.as_view(),
        name='receipt-list-year',
    ),
    path(
        '<slug:entity_slug>/quarter/<int:year>/q<int:quarter>/',
        views.ReceiptModelQuarterListView.as_view(),
        name='receipt-list-quarter',
    ),
    path(
        '<slug:entity_slug>/month/<int:year>/<int:month>/',
        views.ReceiptModelMonthListView.as_view(),
        name='receipt-list-month',
    ),
    path(
        '<slug:entity_slug>/detail/<uuid:receipt_pk>/',
        views.ReceiptModelDetailView.as_view(),
        name='receipt-detail',
    ),
    path(
        '<slug:entity_slug>/delete/<uuid:receipt_pk>/',
        views.ReceiptModelDeleteView.as_view(),
        name='receipt-delete',
    ),
    # Filtered lists
    path(
        '<slug:entity_slug>/type/<str:receipt_type>/',
        views.ReceiptModelListView.as_view(),
        name='receipt-list-type',
    ),
    path(
        '<slug:entity_slug>/vendor/<uuid:vendor_pk>/',
        views.ReceiptModelListView.as_view(),
        name='receipt-list-vendor',
    ),
    path(
        '<slug:entity_slug>/customer/<uuid:customer_pk>/',
        views.ReceiptModelListView.as_view(),
        name='receipt-list-customer',
    ),
    # Reports: Vendor
    path(
        '<slug:entity_slug>/report/vendor/<uuid:vendor_pk>/latest/',
        views.VendorReceiptReportListView.as_view(),
        name='receipt-report-vendor',
    ),
    path(
        '<slug:entity_slug>/report/vendor/<uuid:vendor_pk>/year/<int:year>/',
        views.VendorReceiptReportYearListView.as_view(),
        name='receipt-report-vendor-year',
    ),
    path(
        '<slug:entity_slug>/report/vendor/<uuid:vendor_pk>/quarter/<int:year>/q<int:quarter>/',
        views.VendorReceiptReportQuarterListView.as_view(),
        name='receipt-report-vendor-quarter',
    ),
    path(
        '<slug:entity_slug>/report/vendor/<uuid:vendor_pk>/month/<int:year>/<int:month>/',
        views.VendorReceiptReportMonthListView.as_view(),
        name='receipt-report-vendor-month',
    ),
    # Reports: Customer
    path(
        '<slug:entity_slug>/report/customer/<uuid:customer_pk>/latest/',
        views.CustomerReceiptReportListView.as_view(),
        name='receipt-report-customer',
    ),
    path(
        '<slug:entity_slug>/report/customer/<uuid:customer_pk>/year/<int:year>/',
        views.CustomerReceiptReportYearListView.as_view(),
        name='receipt-report-customer-year',
    ),
    path(
        '<slug:entity_slug>/report/customer/<uuid:customer_pk>/quarter/<int:year>/q<int:quarter>/',
        views.CustomerReceiptReportQuarterListView.as_view(),
        name='receipt-report-customer-quarter',
    ),
    path(
        '<slug:entity_slug>/report/customer/<uuid:customer_pk>/month/<int:year>/<int:month>/',
        views.CustomerReceiptReportMonthListView.as_view(),
        name='receipt-report-customer-month',
    ),
]
