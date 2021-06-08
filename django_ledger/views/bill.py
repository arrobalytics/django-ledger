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
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.generic import (UpdateView, CreateView, DeleteView,
                                  View, ArchiveIndexView, MonthArchiveView, YearArchiveView,
                                  DetailView)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.bill import BillModelCreateForm, BillModelUpdateForm, BillItemFormset, BillModelConfigureForm
from django_ledger.models import EntityModel
from django_ledger.models.bill import BillModel
from django_ledger.utils import new_bill_protocol, mark_accruable_paid
from django_ledger.views.mixins import LoginRequiredMixIn


class BillModelListView(LoginRequiredMixIn, ArchiveIndexView):
    template_name = 'django_ledger/bill_list.html'
    context_object_name = 'bills'
    PAGE_TITLE = _('Bill List')
    date_field = 'date'
    paginate_by = 10
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('vendor').order_by('-date')

    def get_allow_future(self):
        allow_future = self.request.GET.get('allow_future')
        if allow_future:
            try:
                allow_future = int(allow_future)
                if allow_future in (0, 1):
                    return bool(allow_future)
            except ValueError:
                pass
        return False


class BillModelYearListView(YearArchiveView, BillModelListView):
    paginate_by = 10
    make_object_list = True


class BillModelMonthListView(MonthArchiveView, BillModelListView):
    paginate_by = 10
    month_format = '%m'
    date_list_period = 'year'


class BillModelCreateView(LoginRequiredMixIn, CreateView):
    template_name = 'django_ledger/bill_create.html'
    PAGE_TITLE = _('Create Bill')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'uil:bill'
    }

    def get_form(self, form_class=None):
        entity_slug = self.kwargs['entity_slug']
        form = BillModelCreateForm(entity_slug=entity_slug,
                                   user_model=self.request.user,
                                   **self.get_form_kwargs())
        return form

    def form_valid(self, form):
        form.instance = new_bill_protocol(
            bill_model=form.instance,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        )
        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        return reverse('django_ledger:bill-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })


class BillModelUpdateView(LoginRequiredMixIn, UpdateView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill'
    template_name = 'django_ledger/bill_update.html'
    extra_context = {
        'header_subtitle_icon': 'uil:bill'
    }

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        return form_class(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_form_class(self):
        bill_model: BillModel = self.object
        if not bill_model.is_configured():
            return BillModelConfigureForm
        return BillModelUpdateForm

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        bill_model = self.object
        title = f'Bill {bill_model.bill_number}'
        context['page_title'] = title
        context['header_title'] = title

        if not bill_model.is_configured():
            messages.add_message(
                request=self.request,
                message=f'Bill {bill_model.bill_number} must have all accounts configured.',
                level=messages.ERROR,
                extra_tags='is-danger'
            )

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

        bill_model: BillModel = self.object
        bill_item_queryset, item_data = bill_model.get_bill_item_data(
            queryset=bill_model.itemthroughmodel_set.select_related(
                'item_model', 'po_model', 'bill_model').all()
        )
        context['item_formset'] = BillItemFormset(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            bill_pk=bill_model.uuid,
            queryset=bill_item_queryset
        )
        context['total_amount_due'] = item_data['amount_due']
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        bill_pk = self.kwargs['bill_pk']
        return reverse('django_ledger:bill-detail',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': bill_pk
                       })

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).prefetch_related(
            'itemthroughmodel_set'
        ).select_related('ledger', 'vendor')

    def form_valid(self, form):
        form.save(commit=False)
        messages.add_message(self.request,
                             messages.SUCCESS,
                             f'Bill {self.object.bill_number} successfully updated.',
                             extra_tags='is-success')
        return super().form_valid(form)


class BillModelItemsUpdateView(LoginRequiredMixIn, View):
    http_method_names = ['post']

    def post(self, request, entity_slug, bill_pk, **kwargs):
        bill_item_formset: BillItemFormset = BillItemFormset(request.POST,
                                                             user_model=self.request.user,
                                                             bill_pk=bill_pk,
                                                             entity_slug=entity_slug)

        if bill_item_formset.is_valid():
            invoice_items = bill_item_formset.save(commit=False)

            if bill_item_formset.has_changed():
                bill_qs = BillModel.objects.for_entity(
                    user_model=self.request.user,
                    entity_slug=entity_slug
                )
                bill_model: BillModel = get_object_or_404(bill_qs, uuid__exact=bill_pk)

                entity_qs = EntityModel.objects.for_user(
                    user_model=self.request.user
                )
                entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)

                for item in invoice_items:
                    item.entity = entity_model
                    item.bill_model = bill_model

                bill_item_list = bill_item_formset.save()
                # todo: pass item list to update_amount_due...?
                bill_model.update_amount_due()
                bill_model.new_state(commit=True)
                bill_model.clean()
                bill_model.save(update_fields=['amount_due',
                                               'amount_receivable',
                                               'amount_unearned',
                                               'amount_earned',
                                               'updated'])

                bill_model.migrate_state(
                    entity_slug=entity_slug,
                    user_model=self.request.user,
                    item_models=bill_item_list,
                    force_migrate=True
                )

        return HttpResponseRedirect(reverse('django_ledger:bill-update',
                                            kwargs={
                                                'entity_slug': entity_slug,
                                                'bill_pk': bill_pk
                                            }))


class BillModelDetailView(LoginRequiredMixIn, DetailView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill'
    template_name = 'django_ledger/bill_detail.html'
    extra_context = {
        'header_subtitle_icon': 'uil:bill',
        'hide_menu': True
    }

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        bill_model: BillModel = self.object
        title = f'Bill {bill_model.bill_number}'
        context['page_title'] = title
        context['header_title'] = title

        bill_model: BillModel = self.object
        bill_items_qs, item_data = bill_model.get_bill_item_data(
            queryset=bill_model.itemthroughmodel_set.all()
        )
        context['bill_items'] = bill_items_qs
        context['total_amount_due'] = item_data['amount_due']

        if not bill_model.is_configured():
            link = format_html(f"""
            <a href="{reverse("django_ledger:bill-update", kwargs={
                'entity_slug': self.kwargs['entity_slug'],
                'bill_pk': bill_model.uuid
            })}">here</a>
            """)
            msg = f'Bill {bill_model.bill_number} has not been fully set up. ' + \
                  f'Please update or assign associated accounts {link}.'
            messages.add_message(self.request,
                                 message=msg,
                                 level=messages.WARNING,
                                 extra_tags='is-danger')
        return context

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).prefetch_related(
            'itemthroughmodel_set', 'ledger__journal_entries__entity_unit'
        ).select_related('ledger', 'vendor', 'cash_account', 'prepaid_account', 'unearned_account')


class BillModelDeleteView(LoginRequiredMixIn, DeleteView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill'
    template_name = 'django_ledger/bill_delete.html'
    extra_context = {
        'hide_menu': True,
        'header_subtitle_icon': 'uil:bill'
    }

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = _('Delete Bill ') + self.object.bill_number
        context['header_title'] = context['page_title']
        return context

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_success_url(self):
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                       })


class BillModelMarkPaidView(LoginRequiredMixIn,
                            View,
                            SingleObjectMixin):
    http_method_names = ['post']
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('ledger')

    def post(self, request, *args, **kwargs):
        bill: BillModel = self.get_object()
        mark_accruable_paid(
            accruable_model=bill,
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )
        messages.add_message(request,
                             messages.SUCCESS,
                             f'Successfully marked bill {bill.bill_number} as Paid.',
                             extra_tags='is-success')
        redirect_url = reverse('django_ledger:bill-detail',
                               kwargs={
                                   'entity_slug': self.kwargs['entity_slug'],
                                   'bill_pk': bill.uuid
                               })
        return HttpResponseRedirect(redirect_url)
