"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Customer Estimate views grouped by CRUD + Actions.

  * CREATE   — EstimateModelCreateView
  * RETRIEVE — EstimateModelListView, EstimateModelDetailView
  * UPDATE   — EstimateModelUpdateView
  * ACTIONS  — BaseEstimateActionView and mark-as-* helpers
"""

from typing import Optional

from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ArchiveIndexView, CreateView, DetailView, UpdateView

from django_ledger.forms.estimate import (
    EstimateModelCreateForm,
    BaseEstimateModelUpdateForm,
    CanEditEstimateItemModelFormset,
    ReadOnlyEstimateItemModelFormset,
    DraftEstimateModelUpdateForm,
)
from django_ledger.models import EntityModel
from django_ledger.models.estimate import EstimateModel, EstimateModelQuerySet
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, DjangoLedgerActionView


class EstimateModelModelBaseView(DjangoLedgerSecurityMixIn):
    """Entity-scoped estimate queryset shared by all estimate CRUD/action views."""

    queryset: Optional[EstimateModelQuerySet] = None

    def get_queryset(self) -> EstimateModelQuerySet:
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            qs: EstimateModelQuerySet = entity_model.estimatemodel_set.select_related('customer', 'entity')
            self.queryset = qs
        return super().get_queryset()


# -----------------
# RETRIEVE (List)
# -----------------
class EstimateModelListView(EstimateModelModelBaseView, ArchiveIndexView):
    template_name = 'django_ledger/estimate/estimate_list.html'
    context_object_name = 'estimate_list'
    PAGE_TITLE = _('Customer Estimates')
    date_field = 'created'
    paginate_by = 20
    paginate_orphans = 2
    allow_empty = True
    extra_context = {'page_title': PAGE_TITLE, 'header_title': PAGE_TITLE, 'header_subtitle_icon': 'eos-icons:job'}


# -----------------
# CREATE
# -----------------
class EstimateModelCreateView(EstimateModelModelBaseView, CreateView):
    PAGE_TITLE = _('Create Customer Estimate')
    extra_context = {'page_title': PAGE_TITLE, 'header_title': PAGE_TITLE, 'header_subtitle_icon': 'eos-icons:job'}
    template_name = 'django_ledger/estimate/estimate_create.html'

    def get_form_class(self):
        return EstimateModelCreateForm

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        return form_class(
            entity_slug=self.kwargs['entity_slug'], user_model=self.request.user, **self.get_form_kwargs()
        )

    def get_success_url(self):
        cj_model: EstimateModel = self.object
        return reverse(
            'django_ledger:customer-estimate-detail',
            kwargs={'entity_slug': self.kwargs['entity_slug'], 'ce_pk': cj_model.uuid},
        )

    def form_valid(self, form):
        estimate_model: EstimateModel = form.save(commit=False)
        estimate_model.entity = self.AUTHORIZED_ENTITY_MODEL
        return super(EstimateModelCreateView, self).form_valid(form)


# -----------------
# RETRIEVE (Detail)
# -----------------
class EstimateModelDetailView(EstimateModelModelBaseView, DetailView):
    pk_url_kwarg = 'ce_pk'
    template_name = 'django_ledger/estimate/estimate_detail.html'
    PAGE_TITLE = _('Customer Estimate Detail')
    context_object_name = 'estimate_model'
    extra_context = {'hide_menu': True}
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        context = super(EstimateModelDetailView, self).get_context_data(**kwargs)
        ce_model: EstimateModel = self.object
        context['page_title'] = self.PAGE_TITLE
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = ce_model.estimate_number
        context['header_subtitle_icon'] = 'eos-icons:job'
        context['estimate_item_list'] = ce_model.itemtransactionmodel_set.all()

        # PO Model Queryset...
        po_qs = (
            ce_model.purchaseordermodel_set.for_entity(entity_model=self.kwargs['entity_slug'])
            if ce_model.is_approved()
            else ce_model.purchaseordermodel_set.none()
        )
        context['estimate_po_model_queryset'] = po_qs

        invoice_qs = (
            ce_model.invoicemodel_set.for_entity(entity_model=self.kwargs['entity_slug'])
            if ce_model.is_approved()
            else ce_model.invoicemodel_set.none()
        )
        context['estimate_invoice_model_queryset'] = invoice_qs

        bill_qs = (
            ce_model.billmodel_set.for_entity(entity_model=self.kwargs['entity_slug'])
            if ce_model.is_approved()
            else ce_model.billmodel_set.none()
        )
        context['estimate_bill_model_queryset'] = bill_qs

        if ce_model.is_contract():
            context['contract_progress'] = ce_model.get_contract_summary(
                po_qs=po_qs, invoice_qs=invoice_qs, bill_qs=bill_qs
            )

        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related('itemtransactionmodel_set')


# -----------------
# UPDATE
# -----------------
class EstimateModelUpdateView(EstimateModelModelBaseView, UpdateView):
    template_name = 'django_ledger/estimate/estimate_update.html'
    pk_url_kwarg = 'ce_pk'
    context_object_name = 'estimate'
    PAGE_TITLE = _('Customer Estimate Update')
    http_method_names = ['get', 'post']

    action_update_items = False

    def get_form_class(self):
        estimate_model: EstimateModel = self.object
        if estimate_model.is_draft():
            return DraftEstimateModelUpdateForm
        return BaseEstimateModelUpdateForm

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        return form_class(
            entity_slug=self.kwargs['entity_slug'], user_model=self.request.user, **self.get_form_kwargs()
        )

    def get_context_data(self, itemtxs_formset=None, **kwargs):
        context = super(EstimateModelUpdateView, self).get_context_data(**kwargs)
        ce_model: EstimateModel = self.object
        context['page_title'] = self.PAGE_TITLE
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = ce_model.title
        context['header_subtitle_icon'] = 'eos-icons:job'
        if not itemtxs_formset:
            itemtxs_qs, _ = ce_model.get_itemtxs_data()
            itemtxs_agg = itemtxs_qs.get_estimate_aggregate()
            if ce_model.can_update_items():
                itemtxs_formset = CanEditEstimateItemModelFormset(
                    entity_slug=self.kwargs['entity_slug'],
                    user_model=self.request.user,
                    customer_job_model=ce_model,
                    queryset=itemtxs_qs,
                )
            else:
                itemtxs_formset = ReadOnlyEstimateItemModelFormset(
                    entity_slug=self.kwargs['entity_slug'],
                    user_model=self.request.user,
                    customer_job_model=ce_model,
                    queryset=itemtxs_qs,
                )
        else:
            itemtxs_qs, _ = ce_model.get_itemtxs_data(queryset=itemtxs_formset.queryset)
            itemtxs_agg = itemtxs_qs.get_estimate_aggregate()

        context['ce_revenue_estimate__sum'] = itemtxs_agg['ce_revenue_estimate__sum']
        context['ce_cost_estimate__sum'] = itemtxs_agg['ce_cost_estimate__sum']
        context['itemtxs_qs'] = itemtxs_qs
        context['itemtxs_formset'] = itemtxs_formset
        return context

    def get_success_url(self):
        return reverse(
            'django_ledger:customer-estimate-detail',
            kwargs={'entity_slug': self.kwargs['entity_slug'], 'ce_pk': self.kwargs['ce_pk']},
        )

    def get(self, request, entity_slug, ce_pk, *args, **kwargs):
        if self.action_update_items:
            return HttpResponseRedirect(
                redirect_to=reverse(
                    'django_ledger:customer-estimate-update', kwargs={'entity_slug': entity_slug, 'ce_pk': ce_pk}
                )
            )
        return super(EstimateModelUpdateView, self).get(request, entity_slug, ce_pk, *args, **kwargs)

    def post(self, request, entity_slug, ce_pk, *args, **kwargs):
        if self.action_update_items:
            if not request.user.is_authenticated:
                return HttpResponseForbidden()

            queryset = self.get_queryset()
            ce_model: EstimateModel = self.get_object(queryset=queryset)
            self.object = ce_model
            itemtxs_formset: CanEditEstimateItemModelFormset = CanEditEstimateItemModelFormset(
                request.POST, user_model=self.request.user, customer_job_model=ce_model, entity_slug=entity_slug
            )
            if itemtxs_formset.has_changed():
                if itemtxs_formset.is_valid():
                    itemtxs_list = itemtxs_formset.save(commit=False)
                    entity_qs = EntityModel.objects.for_user(user_model=self.request.user)
                    entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)

                    for itemtxs in itemtxs_list:
                        itemtxs.ce_model_id = ce_model.uuid
                        itemtxs.clean()

                    itemtxs_list = itemtxs_formset.save()

                    ce_model.update_state()
                    ce_model.clean()
                    ce_model.save(
                        update_fields=[
                            'revenue_estimate',
                            'labor_estimate',
                            'equipment_estimate',
                            'material_estimate',
                            'other_estimate',
                            'updated',
                        ]
                    )

                    messages.add_message(
                        request,
                        message=f'Customer estimate items saved.',
                        level=messages.SUCCESS,
                        extra_tags='is-success',
                    )

                    return self.render_to_response(context=self.get_context_data())
            context = self.get_context_data(itemtxs_formset=itemtxs_formset)
            return self.render_to_response(context=context)
        return super(EstimateModelUpdateView, self).post(request, *args, **kwargs)


# -----------------
# ACTIONS (status)
# -----------------
class BaseEstimateActionView(EstimateModelModelBaseView, DjangoLedgerActionView):
    """
    Shared customer-estimate action endpoint.

    Invokes an EstimateModel status method, then redirects to estimate update.
    Unlike other action bases, only ``commit`` is passed to the model method.
    Requires POST by default unless legacy GET is enabled in settings.
    """

    pk_url_kwarg = 'ce_pk'
    pass_user_model_to_kwargs = False

    def get_redirect_url(self, entity_slug, ce_pk, *args, **kwargs):
        return reverse('django_ledger:customer-estimate-update', kwargs={'entity_slug': entity_slug, 'ce_pk': ce_pk})

    def get_action_kwargs(self, **kwargs):
        # Preserve prior call signature: commit only.
        return {'commit': self.commit}


class EstimateActionMarkAsDraftView(BaseEstimateActionView):
    """Returns the customer estimate to draft for further editing."""

    action_name = 'mark_as_draft'


class EstimateActionMarkAsReviewView(BaseEstimateActionView):
    """Submits the estimate for review before customer approval."""

    action_name = 'mark_as_review'


class EstimateActionMarkAsApprovedView(BaseEstimateActionView):
    """Marks the estimate as approved by the customer / internal review."""

    action_name = 'mark_as_approved'


class EstimateActionMarkAsCompletedView(BaseEstimateActionView):
    """Marks the estimate as completed once related work is finished."""

    action_name = 'mark_as_completed'


class EstimateActionMarkAsCanceledView(BaseEstimateActionView):
    """Cancels an estimate that will not proceed to contracts or invoices."""

    action_name = 'mark_as_canceled'


class EstimateActionMarkAsVoidView(BaseEstimateActionView):
    action_name = 'mark_as_void'
