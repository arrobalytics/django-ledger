"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Invoice views grouped by CRUD + Actions.

  * CREATE   — InvoiceModelCreateView
  * RETRIEVE — InvoiceModelListView / Year / Month, InvoiceModelDetailView
  * UPDATE   — InvoiceModelUpdateView (and item-update variant)
  * DELETE   — InvoiceModelDeleteView
  * ACTIONS  — BaseInvoiceActionView and mark-as-* / ledger helpers

Querysets are entity-scoped; views require DjangoLedgerSecurityMixIn.
"""

from typing import Optional

from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    UpdateView,
    CreateView,
    DeleteView,
    MonthArchiveView,
    ArchiveIndexView,
    YearArchiveView,
    DetailView,
)

from django_ledger.forms.invoice import (
    BaseInvoiceModelUpdateForm,
    InvoiceModelCreateForEstimateForm,
    get_invoice_itemtxs_formset_class,
    DraftInvoiceModelUpdateForm,
    InReviewInvoiceModelUpdateForm,
    ApprovedInvoiceModelUpdateForm,
    PaidInvoiceModelUpdateForm,
    AccruedAndApprovedInvoiceModelUpdateForm,
    InvoiceModelCreateForm,
)
from django_ledger.io.io_core import get_localdate
from django_ledger.models import EntityModel, LedgerModel, EstimateModel
from django_ledger.models.invoice import InvoiceModel, InvoiceModelQuerySet
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, DjangoLedgerActionView


class InvoiceModelModelBaseView(DjangoLedgerSecurityMixIn):
    """Entity-scoped invoice queryset shared by all invoice CRUD/action views."""

    queryset: Optional[InvoiceModelQuerySet] = None

    def get_queryset(self) -> InvoiceModelQuerySet:
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            qs: InvoiceModelQuerySet = (
                InvoiceModel.objects.for_entity(entity_model=entity_model)
                .select_related('customer', 'ledger')
                .order_by('-created')
            )
            self.queryset = qs
        return super().get_queryset()


# -----------------
# RETRIEVE (List)
# -----------------
class InvoiceModelListView(InvoiceModelModelBaseView, ArchiveIndexView):
    template_name = 'django_ledger/invoice/invoice_list.html'
    context_object_name = 'invoice_list'
    PAGE_TITLE = _('Invoice List')
    date_field = 'created'
    paginate_by = 20
    paginate_orphans = 2
    allow_empty = True
    extra_context = {'page_title': PAGE_TITLE, 'header_title': PAGE_TITLE}


class InvoiceModelYearlyListView(YearArchiveView, InvoiceModelListView):
    paginate_by = 10
    make_object_list = True


class InvoiceModelMonthlyListView(MonthArchiveView, InvoiceModelListView):
    paginate_by = 10
    month_format = '%m'


# -----------------
# CREATE
# -----------------
class InvoiceModelCreateView(InvoiceModelModelBaseView, CreateView):
    template_name = 'django_ledger/invoice/invoice_create.html'
    PAGE_TITLE = _('Create Invoice')
    extra_context = {'page_title': PAGE_TITLE, 'header_title': PAGE_TITLE}
    for_estimate = False

    def get(self, request, entity_slug, **kwargs):

        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        if self.for_estimate and 'ce_pk' in self.kwargs:
            estimate_qs = EstimateModel.objects.for_entity(entity_slug=entity_slug, user_model=self.request.user)
            estimate_model: EstimateModel = get_object_or_404(estimate_qs, uuid__exact=self.kwargs['ce_pk'])
            if not estimate_model.can_bind():
                return HttpResponseNotFound('404 Not Found')
        return super(InvoiceModelCreateView, self).get(request, entity_slug, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(InvoiceModelCreateView, self).get_context_data(**kwargs)

        if self.for_estimate:
            context['form_action_url'] = reverse(
                'django_ledger:invoice-create-estimate',
                kwargs={'entity_slug': self.kwargs['entity_slug'], 'ce_pk': self.kwargs['ce_pk']},
            )
            estimate_qs = EstimateModel.objects.for_entity(
                entity_model=self.AUTHORIZED_ENTITY_MODEL,
            ).select_related('customer')
            estimate_model = get_object_or_404(estimate_qs, uuid__exact=self.kwargs['ce_pk'])
            context['estimate_model'] = estimate_model
        else:
            context['form_action_url'] = reverse(
                'django_ledger:invoice-create', kwargs={'entity_slug': self.kwargs['entity_slug']}
            )
        return context

    def get_initial(self):
        return {'date_draft': get_localdate()}

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        if self.for_estimate:
            InvoiceModelCreateForEstimateForm(
                entity_slug=entity_slug, user_model=self.request.user, **self.get_form_kwargs()
            )
        return InvoiceModelCreateForm(entity_slug=entity_slug, user_model=self.request.user, **self.get_form_kwargs())

    def form_valid(self, form):
        invoice_model: InvoiceModel = form.save(commit=False)
        ledger_model, invoice_model = invoice_model.configure(
            entity_slug=self.AUTHORIZED_ENTITY_MODEL, commit_ledger=True
        )

        if self.for_estimate:
            ce_pk = self.kwargs['ce_pk']
            estimate_model_qs = EstimateModel.objects.for_entity(
                entity_model=self.AUTHORIZED_ENTITY_MODEL,
            )

            estimate_model = get_object_or_404(estimate_model_qs, uuid__exact=ce_pk)
            invoice_model.bind_estimate(estimate_model=estimate_model, commit=False)

        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        invoice_model: InvoiceModel = self.object
        if self.for_estimate:
            return reverse(
                'django_ledger:customer-estimate-detail',
                kwargs={'entity_slug': entity_slug, 'ce_pk': self.kwargs['ce_pk']},
            )
        return reverse(
            'django_ledger:invoice-detail', kwargs={'entity_slug': entity_slug, 'invoice_pk': invoice_model.uuid}
        )


# -----------------
# UPDATE
# -----------------
class InvoiceModelUpdateView(InvoiceModelModelBaseView, UpdateView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    context_object_name = 'invoice'
    template_name = 'django_ledger/invoice/invoice_update.html'
    form_class = BaseInvoiceModelUpdateForm
    http_method_names = ['get', 'post']

    action_update_items = False

    def get_form_class(self):
        invoice_model: InvoiceModel = self.object

        if invoice_model.is_draft():
            return DraftInvoiceModelUpdateForm
        elif invoice_model.is_review():
            return InReviewInvoiceModelUpdateForm
        elif invoice_model.is_approved():
            if invoice_model.accrue:
                return AccruedAndApprovedInvoiceModelUpdateForm
            return ApprovedInvoiceModelUpdateForm
        elif invoice_model.is_paid():
            return PaidInvoiceModelUpdateForm
        return BaseInvoiceModelUpdateForm

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        if self.request.method == 'POST' and self.action_update_items:
            return form_class(
                entity_slug=self.kwargs['entity_slug'], user_model=self.request.user, instance=self.object
            )
        return form_class(
            entity_slug=self.kwargs['entity_slug'], user_model=self.request.user, **self.get_form_kwargs()
        )

    def get_context_data(self, itemtxs_formset=None, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice_model: InvoiceModel = self.object
        title = f'Invoice {invoice_model.invoice_number}'
        context['page_title'] = title
        context['header_title'] = title

        ledger_model: LedgerModel = self.object.ledger

        if not invoice_model.is_configured():
            messages.add_message(
                request=self.request,
                message=f'Invoice {invoice_model.invoice_number} must have all accounts configured.',
                level=messages.ERROR,
                extra_tags='is-danger',
            )

        if not invoice_model.is_paid():
            if ledger_model.locked:
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    'Warning! This invoice is locked. Must unlock before making any changes.',
                    extra_tags='is-danger',
                )

        if ledger_model.locked:
            messages.add_message(
                self.request,
                messages.ERROR,
                'Warning! This Invoice is Locked. Must unlock before making any changes.',
                extra_tags='is-danger',
            )

        if not ledger_model.is_posted():
            messages.add_message(
                self.request,
                messages.INFO,
                'This Invoice has not been posted. Must post to see ledger changes.',
                extra_tags='is-info',
            )

        if not itemtxs_formset:
            itemtxs_qs = invoice_model.itemtransactionmodel_set.all().select_related('item_model')
            itemtxs_qs, itemtxs_agg = invoice_model.get_itemtxs_data(queryset=itemtxs_qs)
            invoice_itemtxs_formset_class = get_invoice_itemtxs_formset_class(invoice_model)
            itemtxs_formset = invoice_itemtxs_formset_class(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                invoice_model=invoice_model,
                queryset=itemtxs_qs,
            )
        else:
            itemtxs_qs, itemtxs_agg = invoice_model.get_itemtxs_data(queryset=itemtxs_formset.queryset)

        context['itemtxs_formset'] = itemtxs_formset
        context['total_amount__sum'] = itemtxs_agg['total_amount__sum']
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        invoice_pk = self.kwargs['invoice_pk']
        return reverse('django_ledger:invoice-update', kwargs={'entity_slug': entity_slug, 'invoice_pk': invoice_pk})

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related('itemtransactionmodel_set')

    def form_valid(self, form):
        invoice_model: InvoiceModel = form.save(commit=False)
        if invoice_model.can_migrate():
            invoice_model.migrate_state(user_model=self.request.user, entity_slug=self.kwargs['entity_slug'])
        messages.add_message(
            self.request,
            messages.SUCCESS,
            f'Invoice {self.object.invoice_number} successfully updated.',
            extra_tags='is-success',
        )
        return super().form_valid(form)

    def get(self, request, entity_slug, invoice_pk, *args, **kwargs):
        if self.action_update_items:
            return HttpResponseRedirect(
                redirect_to=reverse(
                    'django_ledger:invoice-update', kwargs={'entity_slug': entity_slug, 'invoice_pk': invoice_pk}
                )
            )
        return super(InvoiceModelUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, entity_slug, invoice_pk, *args, **kwargs):
        if self.action_update_items:
            if not request.user.is_authenticated:
                return HttpResponseForbidden()

            queryset = self.get_queryset()
            invoice_model = self.get_object(queryset=queryset)
            self.object = invoice_model
            invoice_itemtxs_formset_class = get_invoice_itemtxs_formset_class(invoice_model)
            itemtxs_formset = invoice_itemtxs_formset_class(
                request.POST, user_model=self.request.user, invoice_model=invoice_model, entity_slug=entity_slug
            )

            if not invoice_model.can_edit_items():
                messages.add_message(
                    request,
                    message=f'Cannot update items once Invoice is {invoice_model.get_invoice_status_display()}',
                    level=messages.ERROR,
                    extra_tags='is-danger',
                )
                context = self.get_context_data(itemtxs_formset=itemtxs_formset)
                return self.render_to_response(context=context)

            if itemtxs_formset.has_changed():
                if itemtxs_formset.is_valid():
                    itemtxs_list = itemtxs_formset.save(commit=False)
                    entity_qs = EntityModel.objects.for_user(user_model=self.request.user)
                    entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)

                    for itemtxs in itemtxs_list:
                        itemtxs.invoice_model_id = invoice_model.uuid
                        itemtxs.clean()

                    itemtxs_list = itemtxs_formset.save()
                    itemtxs_qs = invoice_model.update_amount_due()
                    invoice_model.get_state(commit=True)
                    invoice_model.clean()
                    invoice_model.save(
                        update_fields=['amount_due', 'amount_receivable', 'amount_unearned', 'amount_earned', 'updated']
                    )

                    invoice_model.migrate_state(
                        entity_slug=entity_slug,
                        user_model=self.request.user,
                        raise_exception=False,
                        itemtxs_qs=itemtxs_qs,
                    )

                    messages.add_message(
                        request,
                        message=f'Items for Invoice {invoice_model.invoice_number} saved.',
                        level=messages.SUCCESS,
                        extra_tags='is-success',
                    )
                    return HttpResponseRedirect(
                        redirect_to=reverse(
                            'django_ledger:invoice-update',
                            kwargs={'entity_slug': entity_slug, 'invoice_pk': invoice_pk},
                        )
                    )

                # if not valid, return formset with errors...
                return self.render_to_response(context=self.get_context_data(itemtxs_formset=itemtxs_formset))
        return super(InvoiceModelUpdateView, self).post(request, **kwargs)


# -----------------
# RETRIEVE (Detail)
# -----------------
class InvoiceModelDetailView(InvoiceModelModelBaseView, DetailView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    context_object_name = 'invoice'
    template_name = 'django_ledger/invoice/invoice_detail.html'
    extra_context = {'hide_menu': True}

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        invoice = self.object.invoice_number
        title = f'Invoice {invoice}'
        context['page_title'] = title
        context['header_title'] = title

        invoice_model: InvoiceModel = self.object
        itemtxs_qs, itemtxs_agg = invoice_model.get_itemtxs_data()
        context['itemtxs_qs'] = itemtxs_qs
        context['total_amount_due'] = itemtxs_agg['total_amount__sum']
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related(
            'ledger',
            'ledger__entity',
            'customer',
            'cash_account',
            'prepaid_account',
            'unearned_account',
            'cash_account__coa_model',
            'prepaid_account__coa_model',
            'unearned_account__coa_model',
        )


# -----------------
# DELETE
# -----------------
class InvoiceModelDeleteView(InvoiceModelModelBaseView, DeleteView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    template_name = 'django_ledger/invoice/invoice_delete.html'
    context_object_name = 'invoice'
    extra_context = {'hide_menu': True}

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = _('Delete Invoice ') + self.object.invoice_number
        context['header_title'] = context['page_title']
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-dashboard', kwargs={'entity_slug': self.kwargs['entity_slug']})


# -----------------
# ACTIONS (status / ledger)
# -----------------
class BaseInvoiceActionView(InvoiceModelModelBaseView, DjangoLedgerActionView):
    """
    Shared invoice action endpoint.

    Invokes an InvoiceModel status or ledger method, then redirects to invoice
    update. Concrete subclasses only set ``action_name``. Requires POST by
    default unless legacy GET actions are enabled in settings.
    """

    pk_url_kwarg = 'invoice_pk'

    def get_redirect_url(self, *args, **kwargs):
        return reverse(
            'django_ledger:invoice-update',
            kwargs={'entity_slug': kwargs['entity_slug'], 'invoice_pk': kwargs['invoice_pk']},
        )


class InvoiceModelActionMarkAsDraftView(BaseInvoiceActionView):
    """Moves the invoice back to draft for further editing."""

    action_name = 'mark_as_draft'


class InvoiceModelActionMarkAsReviewView(BaseInvoiceActionView):
    """Submits the invoice for review before approval."""

    action_name = 'mark_as_review'


class InvoiceModelActionMarkAsApprovedView(BaseInvoiceActionView):
    """Approves the invoice and posts related ledger activity when configured."""

    action_name = 'mark_as_approved'


class InvoiceModelActionMarkAsPaidView(BaseInvoiceActionView):
    """Records the invoice as fully paid / collected."""

    action_name = 'mark_as_paid'


class InvoiceModelActionMarkAsCanceledView(BaseInvoiceActionView):
    """Cancels an invoice that has not been fully posted or paid."""

    action_name = 'mark_as_canceled'


class InvoiceModelActionMarkAsVoidView(BaseInvoiceActionView):
    """Voids an approved or paid invoice and reverses its accounting impact."""

    action_name = 'mark_as_void'


class InvoiceModelActionLockLedgerView(BaseInvoiceActionView):
    """Locks the invoice ledger to prevent further journal edits."""

    action_name = 'lock_ledger'


class InvoiceModelActionUnlockLedgerView(BaseInvoiceActionView):
    """Unlocks the invoice ledger so journal entries can be edited again."""

    action_name = 'unlock_ledger'


class InvoiceModelActionForceMigrateView(BaseInvoiceActionView):
    """Force-migrates invoice ledger state when balances need reconciliation."""

    action_name = 'migrate_state'

    def get_redirect_url(self, entity_slug, invoice_pk, *args, **kwargs):
        return reverse('django_ledger:invoice-update', kwargs={'entity_slug': entity_slug, 'invoice_pk': invoice_pk})
