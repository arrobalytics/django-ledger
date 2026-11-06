"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Vendor views grouped by CRUD.

  * CREATE   — VendorModelCreateView
  * RETRIEVE — VendorModelListView, VendorModelDetailView
  * UPDATE   — VendorModelUpdateView

Querysets are entity-scoped via VendorModelModelBaseView after
DjangoLedgerSecurityMixIn authorizes the entity slug.
"""

from typing import Optional

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from django_ledger.forms.vendor import VendorModelForm
from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.vendor import VendorModel, VendorModelQuerySet
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class VendorModelModelBaseView(DjangoLedgerSecurityMixIn):
    """Entity-scoped vendor queryset shared by all vendor CRUD views."""

    queryset: Optional[VendorModelQuerySet] = None

    def get_queryset(self) -> VendorModelQuerySet:
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            qs: VendorModelQuerySet = VendorModel.objects.for_entity(entity_model=entity_model).order_by('-updated')
            self.queryset = qs
        return super().get_queryset()


# -----------------
# RETRIEVE (List)
# -----------------
class VendorModelListView(VendorModelModelBaseView, ListView):
    """Lists vendors belonging to the authorized entity."""

    template_name = 'django_ledger/vendor/vendor_list.html'
    context_object_name = 'vendor_list'
    PAGE_TITLE = _('Vendor List')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'bi:person-lines-fill',
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entity_model: EntityModel = self.get_authorized_entity_instance()
        context['header_subtitle'] = entity_model.name
        return context


# -----------------
# CREATE
# -----------------
class VendorModelCreateView(VendorModelModelBaseView, CreateView):
    """Creates a vendor bound to the authorized entity."""

    template_name = 'django_ledger/vendor/vendor_create.html'
    PAGE_TITLE = _('Create New Vendor')
    form_class = VendorModelForm
    context_object_name = 'vendor'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'bi:person-lines-fill',
    }

    def get_success_url(self):
        return reverse(
            'django_ledger:vendor-list',
            kwargs={'entity_slug': self.kwargs['entity_slug']},
        )

    def form_valid(self, form):
        vendor_model: VendorModel = form.save(commit=False)
        # Reuse the already-authorized entity — do not re-query by slug alone.
        vendor_model.entity_model = self.get_authorized_entity_instance()
        return super().form_valid(form)


# -----------------
# UPDATE
# -----------------
class VendorModelUpdateView(VendorModelModelBaseView, UpdateView):
    """Updates an existing vendor within the authorized entity."""

    template_name = 'django_ledger/vendor/vendor_update.html'
    PAGE_TITLE = _('Vendor Update')
    context_object_name = 'vendor'
    form_class = VendorModelForm

    slug_url_kwarg = 'vendor_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super(VendorModelUpdateView, self).get_context_data(**kwargs)
        vendor_model: VendorModel = self.object
        context['page_title'] = self.PAGE_TITLE
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = vendor_model.vendor_number
        context['header_subtitle_icon'] = 'bi:person-lines-fill'
        return context

    def get_success_url(self):
        return reverse(
            'django_ledger:vendor-list',
            kwargs={'entity_slug': self.kwargs['entity_slug']},
        )


# -----------------
# RETRIEVE (Detail)
# -----------------
class VendorModelDetailView(VendorModelModelBaseView, DetailView):
    """
    Vendor profile with related receipts and bills.

    Related querysets are constrained to the authorized entity to prevent
    cross-entity leakage of financial documents.
    """

    template_name = 'django_ledger/vendor/vendor_detail.html'
    context_object_name = 'vendor'
    PAGE_TITLE = _('Vendor Details')
    slug_url_kwarg = 'vendor_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        vendor_model: VendorModel = self.object
        receipts_qs = (
            ReceiptModel.objects.for_entity(entity_model=self.AUTHORIZED_ENTITY_MODEL)
            .for_vendor(vendor_model=vendor_model)
            .order_by('-receipt_date')
        )

        bills_qs = (
            BillModel.objects.for_entity(entity_model=self.AUTHORIZED_ENTITY_MODEL)
            .filter(vendor=vendor_model)
            .order_by('-updated')
        )

        context.update(
            {
                'page_title': self.PAGE_TITLE,
                'header_title': self.PAGE_TITLE,
                'header_subtitle': f'{vendor_model.vendor_name} · {vendor_model.vendor_number}',
                'header_subtitle_icon': 'bi:person-lines-fill',
                'receipts': receipts_qs,
                'bills': bills_qs,
            }
        )
        return context
