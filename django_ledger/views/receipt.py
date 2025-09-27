"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

from typing import Optional
from calendar import month_name

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    ArchiveIndexView,
    DeleteView,
    DetailView,
    MonthArchiveView,
    YearArchiveView,
)

from django_ledger.models import CustomerModel, EntityModel, LedgerModel, VendorModel
from django_ledger.models.receipt import ReceiptModel, ReceiptModelQuerySet
from django_ledger.models.transactions import TransactionModel
from django_ledger.views.mixins import (
    DjangoLedgerSecurityMixIn,
    QuarterlyReportMixIn,
)


class BaseReceiptModelViewMixIn(DjangoLedgerSecurityMixIn):
    queryset: Optional[ReceiptModelQuerySet] = None

    def get_queryset(self):
        if self.queryset is None:
            entity_model: EntityModel = self.AUTHORIZED_ENTITY_MODEL
            qs = entity_model.get_receipts()
            qs = qs.select_related(
                'ledger_model', 'customer_model', 'vendor_model'
            ).order_by('-receipt_date', '-created')

            receipt_type = self.kwargs.get('receipt_type')
            if receipt_type:
                qs = qs.filter(receipt_type__exact=receipt_type)
                if receipt_type in [
                    ReceiptModel.SALES_RECEIPT,
                    ReceiptModel.SALES_REFUND,
                ]:
                    qs = qs.filter(
                        customer_model__isnull=False, vendor_model__isnull=True
                    )

                elif receipt_type in [
                    ReceiptModel.EXPENSE_RECEIPT,
                    ReceiptModel.EXPENSE_REFUND,
                ]:
                    qs = qs.filter(
                        vendor_model__isnull=False, customer_model__isnull=True
                    )

            vendor_pk = self.kwargs.get('vendor_pk')
            if vendor_pk:
                qs = qs.for_vendor(vendor_model=vendor_pk)

            customer_pk = self.kwargs.get('customer_pk')
            if customer_pk:
                qs = qs.for_customer(customer_model=customer_pk)

            self.queryset = qs

        return self.queryset


class ReceiptModelListView(BaseReceiptModelViewMixIn, ArchiveIndexView):
    template_name = 'django_ledger/receipt/receipt_list.html'
    context_object_name = 'receipt_list'
    PAGE_TITLE = _('Receipts List')
    date_field = 'receipt_date'
    paginate_by = 20
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'title': PAGE_TITLE,
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'mdi:receipt',
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subtitle = None

        receipt_type = self.kwargs.get('receipt_type')

        if receipt_type:
            context['title'] = ReceiptModel.RECEIPT_TYPES_MAP[receipt_type]

        vendor_pk = self.kwargs.get('vendor_pk')
        if vendor_pk:
            vendor = VendorModel.objects.for_entity(
                entity_model=self.AUTHORIZED_ENTITY_MODEL
            ).get(uuid__exact=vendor_pk)
            subtitle = vendor.vendor_name
        customer_pk = self.kwargs.get('customer_pk')

        if customer_pk:
            customer = CustomerModel.objects.for_entity(
                entity_model=self.AUTHORIZED_ENTITY_MODEL
            ).get(uuid__exact=customer_pk)
            subtitle = customer.customer_name

        if subtitle:
            context['header_subtitle'] = subtitle
        return context


class ReceiptModelYearListView(ReceiptModelListView, YearArchiveView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['year'] = self.get_year()
        context['page_title'] = _(f'Receipts List {self.get_year()}')
        context['header_title'] = _(f'Receipts List {self.get_year()}')
        context['header_subtitle'] = self.AUTHORIZED_ENTITY_MODEL.name
        return context


class ReceiptModelQuarterListView(ReceiptModelYearListView, QuarterlyReportMixIn):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.for_dates(from_date=self.get_from_date(), to_date=self.get_to_date())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _(f'Receipts List Q{self.get_quarter()}')
        context['header_title'] = _(f'Receipts List Q{self.get_quarter()}')
        context['header_subtitle'] = self.AUTHORIZED_ENTITY_MODEL.name
        return context


class ReceiptModelMonthListView(ReceiptModelYearListView, MonthArchiveView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_year()
        month_num = int(self.get_month())
        month_label = month_name[month_num]
        context['page_title'] = _(f'Receipts List {month_label} {year}')
        context['header_title'] = _(f'Receipts List {month_label}, {year}')
        context['header_subtitle'] = self.AUTHORIZED_ENTITY_MODEL.name
        return context


class ReceiptModelDetailView(BaseReceiptModelViewMixIn, DetailView):
    template_name = 'django_ledger/receipt/receipt_detail.html'
    context_object_name = 'receipt'
    slug_field = 'uuid'
    slug_url_kwarg = 'receipt_pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receipt_model: ReceiptModel = self.object
        ledger_model: LedgerModel = receipt_model.ledger_model
        title = _(f'Receipt {receipt_model.receipt_number}')
        context['page_title'] = title
        context['header_title'] = title
        context['header_subtitle'] = receipt_model.receipt_date
        context['header_subtitle_icon'] = 'mdi:receipt'

        tx_list = (
            TransactionModel.objects.for_entity(
                entity_model=self.AUTHORIZED_ENTITY_MODEL
            )
            .for_ledger(ledger_model=ledger_model)
            .posted()
            .not_closing_entry()
            .select_related(
                'account',
                'journal_entry',
                'journal_entry__entity_unit',
            )
            .order_by('journal_entry__timestamp', 'account__code')
        )

        context['tx_list'] = tx_list
        context['staged_tx'] = receipt_model.staged_transaction_model
        if receipt_model.staged_transaction_model_id:
            context['import_job'] = receipt_model.staged_transaction_model.import_job
        return context


# VENDOR VIEWS......
class VendorReceiptReportListView(ReceiptModelListView):
    template_name = 'django_ledger/receipt/vendor_receipt_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor_pk = self.kwargs['vendor_pk']
        vendor_model_qs = VendorModel.objects.for_entity(
            entity_model=self.AUTHORIZED_ENTITY_MODEL
        )
        vendor_model: VendorModel = get_object_or_404(
            vendor_model_qs, uuid__exact=vendor_pk
        )
        context['vendor_model'] = vendor_model
        context['page_title'] = _(f'Vendor Receipts {vendor_model.vendor_name}')
        context['header_title'] = _('Vendor Receipts')
        context['header_subtitle'] = vendor_model.vendor_name
        context['header_subtitle_icon'] = 'mdi:receipt'
        return context


class VendorReceiptReportYearListView(ReceiptModelYearListView):
    template_name = 'django_ledger/receipt/vendor_receipt_report.html'


class VendorReceiptReportQuarterListView(ReceiptModelQuarterListView):
    template_name = 'django_ledger/receipt/vendor_receipt_report.html'


class VendorReceiptReportMonthListView(ReceiptModelMonthListView):
    template_name = 'django_ledger/receipt/vendor_receipt_report.html'


# CUSTOMERS VIEWS......
class CustomerReceiptReportListView(ReceiptModelListView):
    template_name = 'django_ledger/receipt/customer_receipt_report.html'
    allow_empty = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer_model_qs = CustomerModel.objects.for_entity(
            entity_model=self.AUTHORIZED_ENTITY_MODEL
        )
        customer_pk = self.kwargs['customer_pk']
        customer_model = get_object_or_404(
            customer_model_qs,
            uuid__exact=customer_pk,
        )
        context['vendor_model'] = customer_model
        context['page_title'] = _(f'Customer Receipts {customer_model.name}')
        context['header_title'] = _('Customer Receipts')
        context['header_subtitle'] = customer_model.vendor_name
        context['header_subtitle_icon'] = 'mdi:receipt'
        return context


class CustomerReceiptReportYearListView(CustomerReceiptReportListView):
    template_name = 'django_ledger/receipt/customer_receipt_report.html'
    make_object_list = True


class CustomerReceiptReportQuarterListView(ReceiptModelQuarterListView):
    template_name = 'django_ledger/receipt/customer_receipt_report.html'
    make_object_list = True


class CustomerReceiptReportMonthListView(ReceiptModelMonthListView):
    template_name = 'django_ledger/receipt/customer_receipt_report.html'
    month_format = '%m'


class ReceiptModelDeleteView(BaseReceiptModelViewMixIn, DeleteView):
    template_name = 'django_ledger/receipt/receipt_delete.html'
    context_object_name = 'receipt'
    slug_field = 'uuid'
    slug_url_kwarg = 'receipt_pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receipt: ReceiptModel = self.object
        title = _(f'Delete Receipt {receipt.receipt_number}')
        context['page_title'] = title
        context['header_title'] = title
        context['header_subtitle_icon'] = 'mdi:receipt'
        return context

    def can_delete(self, receipt_model: ReceiptModel) -> bool:
        entity_model: EntityModel = self.AUTHORIZED_ENTITY_MODEL
        ce_date = entity_model.get_closing_entry_for_date(
            io_date=receipt_model.receipt_date, inclusive=True
        )
        return ce_date is None

    def delete(self, request, *args, **kwargs):
        receipt_model: ReceiptModel = self.object
        if not receipt_model.can_delete():
            return HttpResponseForbidden(
                'Receipt cannot be deleted because it falls within a closed period.'
            )
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        receipt_model: ReceiptModel = self.object
        return receipt_model.get_list_url()
