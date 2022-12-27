"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import (UpdateView, CreateView, DeleteView, MonthArchiveView,
                                  ArchiveIndexView, YearArchiveView, DetailView, RedirectView)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.invoice import (BaseInvoiceModelUpdateForm, InvoiceModelCreateForEstimateForm,
                                         get_invoice_itemtxs_formset_class,
                                         DraftInvoiceModelUpdateForm, InReviewInvoiceModelUpdateForm,
                                         ApprovedInvoiceModelUpdateForm, PaidInvoiceModelUpdateForm,
                                         AccruedAndApprovedInvoiceModelUpdateForm, InvoiceModelCreateForm)
from django_ledger.models import EntityModel, LedgerModel, EstimateModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class InvoiceModelListView(DjangoLedgerSecurityMixIn, ArchiveIndexView):
    template_name = 'django_ledger/invoice/invoice_list.html'
    context_object_name = 'invoice_list'
    PAGE_TITLE = _('Invoice List')
    date_field = 'created'
    paginate_by = 20
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('customer').order_by('-created')


class InvoiceModelYearlyListView(YearArchiveView, InvoiceModelListView):
    paginate_by = 10
    make_object_list = True


class InvoiceModelMonthlyListView(MonthArchiveView, InvoiceModelListView):
    paginate_by = 10
    month_format = '%m'


class InvoiceModelCreateView(DjangoLedgerSecurityMixIn, CreateView):
    template_name = 'django_ledger/invoice/invoice_create.html'
    PAGE_TITLE = _('Create Invoice')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    for_estimate = False

    def get(self, request, entity_slug, **kwargs):

        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        if self.for_estimate and 'ce_pk' in self.kwargs:
            estimate_qs = EstimateModel.objects.for_entity(
                entity_slug=entity_slug,
                user_model=self.request.user
            )
            estimate_model: EstimateModel = get_object_or_404(estimate_qs, uuid__exact=self.kwargs['ce_pk'])
            if not estimate_model.can_bind():
                return HttpResponseNotFound('404 Not Found')
        return super(InvoiceModelCreateView, self).get(request, entity_slug, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(InvoiceModelCreateView, self).get_context_data(**kwargs)

        if self.for_estimate:
            context['form_action_url'] = reverse('django_ledger:invoice-create-estimate',
                                                 kwargs={
                                                     'entity_slug': self.kwargs['entity_slug'],
                                                     'ce_pk': self.kwargs['ce_pk']
                                                 })
            estimate_qs = EstimateModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('customer')
            estimate_model = get_object_or_404(estimate_qs, uuid__exact=self.kwargs['ce_pk'])
            context['estimate_model'] = estimate_model
        else:
            context['form_action_url'] = reverse('django_ledger:invoice-create',
                                                 kwargs={
                                                     'entity_slug': self.kwargs['entity_slug']
                                                 })
        return context

    def get_initial(self):
        return {
            'date_draft': localdate()
        }

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        if self.for_estimate:
            InvoiceModelCreateForEstimateForm(
                entity_slug=entity_slug,
                user_model=self.request.user,
                **self.get_form_kwargs()
            )
        return InvoiceModelCreateForm(
            entity_slug=entity_slug,
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        invoice_model: InvoiceModel = form.save(commit=False)
        ledger_model, invoice_model = invoice_model.configure(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        )

        if self.for_estimate:
            ce_pk = self.kwargs['ce_pk']
            estimate_model_qs = EstimateModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user)

            estimate_model = get_object_or_404(estimate_model_qs, uuid__exact=ce_pk)
            invoice_model.action_bind_estimate(estimate_model=estimate_model, commit=False)

        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        invoice_model: InvoiceModel = self.object
        if self.for_estimate:
            return reverse('django_ledger:customer-estimate-detail',
                           kwargs={
                               'entity_slug': entity_slug,
                               'ce_pk': self.kwargs['ce_pk']
                           })
        return reverse('django_ledger:invoice-detail',
                       kwargs={
                           'entity_slug': entity_slug,
                           'invoice_pk': invoice_model.uuid
                       })


class InvoiceModelUpdateView(DjangoLedgerSecurityMixIn, UpdateView):
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
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                instance=self.object
            )
        return form_class(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
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
                extra_tags='is-danger'
            )

        if not invoice_model.is_paid():
            if ledger_model.locked:
                messages.add_message(self.request,
                                     messages.ERROR,
                                     f'Warning! This invoice is locked. Must unlock before making any changes.',
                                     extra_tags='is-danger')

        if ledger_model.locked:
            messages.add_message(self.request,
                                 messages.ERROR,
                                 f'Warning! This Invoice is Locked. Must unlock before making any changes.',
                                 extra_tags='is-danger')

        if not ledger_model.is_posted():
            messages.add_message(self.request,
                                 messages.INFO,
                                 f'This Invoice has not been posted. Must post to see ledger changes.',
                                 extra_tags='is-info')

        if not itemtxs_formset:
            itemtxs_qs = invoice_model.itemtransactionmodel_set.all().select_related('item_model')
            itemtxs_qs, itemtxs_agg = invoice_model.get_itemtxs_data(queryset=itemtxs_qs)
            invoice_itemtxs_formset_class = get_invoice_itemtxs_formset_class(invoice_model)
            itemtxs_formset = invoice_itemtxs_formset_class(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                invoice_model=invoice_model,
                queryset=itemtxs_qs
            )
        else:
            itemtxs_qs, itemtxs_agg = invoice_model.get_itemtxs_data(queryset=itemtxs_formset.queryset)

        context['itemtxs_formset'] = itemtxs_formset
        context['total_amount__sum'] = itemtxs_agg['total_amount__sum']
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        invoice_pk = self.kwargs['invoice_pk']
        return reverse('django_ledger:invoice-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'invoice_pk': invoice_pk
                       })

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).prefetch_related('itemtransactionmodel_set').select_related(
            'ledger', 'customer')

    def form_valid(self, form):
        invoice_model: InvoiceModel = form.save(commit=False)
        if invoice_model.can_migrate():
            invoice_model.migrate_state(
                user_model=self.request.user,
                entity_slug=self.kwargs['entity_slug']
            )
        messages.add_message(self.request,
                             messages.SUCCESS,
                             f'Invoice {self.object.invoice_number} successfully updated.',
                             extra_tags='is-success')
        return super().form_valid(form)

    def get(self, request, entity_slug, invoice_pk, *args, **kwargs):
        if self.action_update_items:
            return HttpResponseRedirect(
                redirect_to=reverse('django_ledger:invoice-update',
                                    kwargs={
                                        'entity_slug': entity_slug,
                                        'invoice_pk': invoice_pk
                                    })
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
            itemtxs_formset = invoice_itemtxs_formset_class(request.POST,
                                                            user_model=self.request.user,
                                                            invoice_model=invoice_model,
                                                            entity_slug=entity_slug)

            if not invoice_model.can_edit_items():
                messages.add_message(
                    request,
                    message=f'Cannot update items once Invoice is {invoice_model.get_invoice_status_display()}',
                    level=messages.ERROR,
                    extra_tags='is-danger'
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
                    invoice_model.new_state(commit=True)
                    invoice_model.clean()
                    invoice_model.save(
                        update_fields=['amount_due',
                                       'amount_receivable',
                                       'amount_unearned',
                                       'amount_earned',
                                       'updated']
                    )

                    invoice_model.migrate_state(
                        entity_slug=entity_slug,
                        user_model=self.request.user,
                        raise_exception=False,
                        itemtxs_qs=itemtxs_qs
                    )

                    messages.add_message(request,
                                         message=f'Items for Invoice {invoice_model.invoice_number} saved.',
                                         level=messages.SUCCESS,
                                         extra_tags='is-success')
                    return HttpResponseRedirect(
                        redirect_to=reverse('django_ledger:invoice-update',
                                            kwargs={
                                                'entity_slug': entity_slug,
                                                'invoice_pk': invoice_pk
                                            })
                    )

                # if not valid, return formset with errors...
                return self.render_to_response(context=self.get_context_data(itemtxs_formset=itemtxs_formset))
        return super(InvoiceModelUpdateView, self).post(request, **kwargs)


class InvoiceModelDetailView(DjangoLedgerSecurityMixIn, DetailView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    context_object_name = 'invoice'
    template_name = 'django_ledger/invoice/invoice_detail.html'
    extra_context = {
        'hide_menu': True
    }

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        invoice = self.object.invoice_number
        title = f'Invoice {invoice}'
        context['page_title'] = title
        context['header_title'] = title

        invoice_model: InvoiceModel = self.object
        itemtxs_qs, itemtxs_agg = invoice_model.get_itemtxs_data()
        context['invoice_items'] = itemtxs_qs
        context['total_amount_due'] = itemtxs_agg['total_amount__sum']
        return context

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).prefetch_related(
            'itemtransactionmodel_set'
        ).select_related('ledger', 'customer', 'cash_account', 'prepaid_account', 'unearned_account')


class InvoiceModelDeleteView(DjangoLedgerSecurityMixIn, DeleteView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    template_name = 'django_ledger/invoice/invoice_delete.html'
    context_object_name = 'invoice'
    extra_context = {
        'hide_menu': True
    }

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = _('Delete Invoice ') + self.object.invoice_number
        context['header_title'] = context['page_title']
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )


# ACTION VIEWS...
class BaseInvoiceActionView(DjangoLedgerSecurityMixIn, RedirectView, SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'invoice_pk'
    action_name = None
    commit = True

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:invoice-update',
                       kwargs={
                           'entity_slug': kwargs['entity_slug'],
                           'invoice_pk': kwargs['invoice_pk']
                       })

    def get(self, request, *args, **kwargs):
        kwargs['user_model'] = self.request.user
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(BaseInvoiceActionView, self).get(request, *args, **kwargs)
        invoice_model: InvoiceModel = self.get_object()

        try:
            getattr(invoice_model, self.action_name)(commit=self.commit, **kwargs)
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response


class InvoiceModelActionMarkAsDraftView(BaseInvoiceActionView):
    action_name = 'mark_as_draft'


class InvoiceModelActionMarkAsReviewView(BaseInvoiceActionView):
    action_name = 'mark_as_review'


class InvoiceModelActionMarkAsApprovedView(BaseInvoiceActionView):
    action_name = 'mark_as_approved'


class InvoiceModelActionMarkAsPaidView(BaseInvoiceActionView):
    action_name = 'mark_as_paid'


class InvoiceModelActionMarkAsCanceledView(BaseInvoiceActionView):
    action_name = 'mark_as_canceled'


class InvoiceModelActionMarkAsVoidView(BaseInvoiceActionView):
    action_name = 'mark_as_void'


class InvoiceModelActionLockLedgerView(BaseInvoiceActionView):
    action_name = 'lock_ledger'


class InvoiceModelActionUnlockLedgerView(BaseInvoiceActionView):
    action_name = 'unlock_ledger'


class InvoiceModelActionForceMigrateView(BaseInvoiceActionView):
    action_name = 'migrate_state'

    def get_redirect_url(self, entity_slug, invoice_pk, *args, **kwargs):
        return reverse('django_ledger:invoice-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'invoice_pk': invoice_pk
                       })
