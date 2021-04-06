"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    UpdateView, CreateView, DeleteView, MonthArchiveView,
    ArchiveIndexView, YearArchiveView, DetailView
)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.invoice import InvoiceModelUpdateForm, InvoiceModelCreateForm, InvoiceItemFormset
from django_ledger.models import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.utils import new_invoice_protocol, mark_progressible_paid
from django_ledger.views.mixins import LoginRequiredMixIn


class InvoiceModelListView(LoginRequiredMixIn, ArchiveIndexView):
    template_name = 'django_ledger/invoice_list.html'
    context_object_name = 'invoices'
    PAGE_TITLE = _('Invoice List')
    date_field = 'date'
    paginate_by = 10
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
        ).select_related('customer').order_by('-date')


class InvoiceModelYearlyListView(YearArchiveView, InvoiceModelListView):
    paginate_by = 10
    make_object_list = True


class InvoiceModelMonthlyListView(MonthArchiveView, InvoiceModelListView):
    paginate_by = 10
    month_format = '%m'


class InvoiceModelCreateView(LoginRequiredMixIn, CreateView):
    template_name = 'django_ledger/invoice_create.html'
    PAGE_TITLE = _('Create Invoice')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        form = InvoiceModelCreateForm(
            entity_slug=entity_slug,
            user_model=self.request.user,
            **self.get_form_kwargs())
        return form

    def form_valid(self, form):
        form.instance = new_invoice_protocol(
            invoice_model=form.instance,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        )
        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        return reverse('django_ledger:invoice-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })


class InvoiceModelUpdateView(LoginRequiredMixIn, UpdateView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    context_object_name = 'invoice'
    template_name = 'django_ledger/invoice_update.html'
    form_class = InvoiceModelUpdateForm

    def get_form(self, form_class=None):
        return InvoiceModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        invoice = self.object.invoice_number
        title = f'Invoice {invoice}'
        context['page_title'] = title
        context['header_title'] = title

        ledger_model = self.object.ledger

        if ledger_model.locked:
            messages.add_message(self.request,
                                 messages.ERROR,
                                 f'Warning! This Invoice is Locked. Must unlock before making any changes.',
                                 extra_tags='is-danger')

        if not ledger_model.posted:
            messages.add_message(self.request,
                                 messages.INFO,
                                 f'This Invoice has not been posted. Must post to see ledger changes.',
                                 extra_tags='is-info')

        invoice_model: InvoiceModel = self.object
        invoice_item_queryset, item_data = invoice_model.get_invoice_item_data(
            queryset=invoice_model.invoicemodelitemsthroughmodel_set.all()
        )
        context['item_formset'] = InvoiceItemFormset(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            invoice_pk=self.object.uuid,
            queryset=invoice_item_queryset
        )
        context['total_amount_due'] = item_data['amount_due']
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
        ).prefetch_related('invoicemodelitemsthroughmodel_set').select_related('ledger', 'customer')

    def form_valid(self, form):
        invoice_model: InvoiceModel = form.save(commit=False)
        invoice_model.migrate_state(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        )
        messages.add_message(self.request,
                             messages.SUCCESS,
                             f'Invoice {self.object.invoice_number} successfully updated.',
                             extra_tags='is-success')
        return super().form_valid(form)


class InvoiceModelItemsUpdateView(LoginRequiredMixIn, View):
    http_method_names = ['post']

    def post(self, request, entity_slug, invoice_pk, **kwargs):
        item_formset: InvoiceItemFormset = InvoiceItemFormset(request.POST,
                                                              user_model=self.request.user,
                                                              invoice_pk=invoice_pk,
                                                              entity_slug=entity_slug)

        if item_formset.is_valid():
            invoice_items = item_formset.save(commit=False)

            if item_formset.has_changed():
                invoice_qs = InvoiceModel.objects.for_entity(
                    user_model=self.request.user,
                    entity_slug=entity_slug
                )
                invoice_model: InvoiceModel = get_object_or_404(invoice_qs, uuid__exact=invoice_pk)

                entity_qs = EntityModel.objects.for_user(
                    user_model=self.request.user
                )
                entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)

                for item in invoice_items:
                    item.entity = entity_model
                    item.invoice_model = invoice_model

                item_formset.save()
                invoice_model.update_amount_due()
                invoice_model.new_state(commit=True)
                invoice_model.clean()
                invoice_model.save(update_fields=['amount_due',
                                                  'amount_receivable',
                                                  'amount_unearned',
                                                  'amount_earned',
                                                  'updated'])

                invoice_model.migrate_state(
                    entity_slug=entity_slug,
                    user_model=self.request.user
                )

        return HttpResponseRedirect(reverse('django_ledger:invoice-update',
                                            kwargs={
                                                'entity_slug': entity_slug,
                                                'invoice_pk': invoice_pk
                                            }))


class InvoiceModelDetailView(LoginRequiredMixIn, DetailView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    context_object_name = 'invoice'
    template_name = 'django_ledger/invoice_detail.html'
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
        invoice_items_qs, item_data = invoice_model.get_invoice_item_data(
            queryset=invoice_model.invoicemodelitemsthroughmodel_set.all()
        )
        context['invoice_items'] = invoice_items_qs
        context['total_amount_due'] = item_data['amount_due']
        return context

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).prefetch_related(
            'invoicemodelitemsthroughmodel_set'
        ).select_related('ledger', 'customer', 'cash_account', 'receivable_account', 'payable_account')

class InvoiceModelDeleteView(LoginRequiredMixIn, DeleteView):
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'
    template_name = 'django_ledger/invoice_delete.html'
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

class InvoiceModelMarkPaidView(LoginRequiredMixIn,
                               View,
                               SingleObjectMixin):
    http_method_names = ['post']
    slug_url_kwarg = 'invoice_pk'
    slug_field = 'uuid'

    def get_queryset(self):
        return InvoiceModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('ledger')

    def post(self, request, *args, **kwargs):
        invoice: InvoiceModel = self.get_object()
        mark_progressible_paid(
            progressible_model=invoice,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )
        messages.add_message(request,
                             messages.SUCCESS,
                             f'Successfully marked bill {invoice.invoice_number} as Paid.',
                             extra_tags='is-success')
        redirect_url = reverse('django_ledger:invoice-detail',
                               kwargs={
                                   'entity_slug': self.kwargs['entity_slug'],
                                   'invoice_pk': invoice.uuid
                               })
        return HttpResponseRedirect(redirect_url)
