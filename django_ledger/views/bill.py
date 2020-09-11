from django.contrib import messages
from django.core.exceptions import FieldError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView, CreateView, DeleteView, View, MonthArchiveView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.bill import BillModelCreateForm, BillModelUpdateForm
from django_ledger.models.bill import BillModel
from django_ledger.models.utils import new_bill_protocol


class BillModelListView(MonthArchiveView):
    template_name = 'django_ledger/bill_list.html'
    context_object_name = 'bills'
    PAGE_TITLE = _('Bill List')
    date_field = 'date'
    month_format = '%m'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_year(self):
        try:
            year = self.request.GET['year']
        except KeyError:
            year = localdate().year
        return year

    def get_month(self):
        try:
            month = self.request.GET['month']
        except KeyError:
            month = str(localdate().month)
            month = len(month) * '0' + month
        return month

    def get_queryset(self):
        qs = BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )
        sort = self.request.GET.get('sort')
        if sort:
            try:
                qs = qs.order_by(sort)
            except FieldError:
                messages.add_message(self.request,
                                     level=messages.ERROR,
                                     message=f'Invalid sort {sort}',
                                     extra_tags='is-danger')
        return qs


class BillModelCreateView(CreateView):
    template_name = 'django_ledger/bill_create.html'
    PAGE_TITLE = _('Create Bill')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
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
            user_model=self.request.user
        )
        return super().form_valid(form=form)

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        return reverse('django_ledger:bill-list',
                       kwargs={
                           'entity_slug': entity_slug
                       })


class BillModelUpdateView(UpdateView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill'
    template_name = 'django_ledger/bill_update.html'

    def get_form(self, form_class=None):
        return BillModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        invoice = self.object.bill_number
        title = f'Bill {invoice}'
        context['page_title'] = title
        context['header_title'] = title
        return context

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        bill_pk = self.kwargs['bill_pk']
        return reverse('django_ledger:bill-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'bill_pk': bill_pk
                       })

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('ledger')

    def form_valid(self, form):
        form.save(commit=False)
        messages.add_message(self.request,
                             messages.SUCCESS,
                             f'Bill {self.object.bill_number} successfully updated.',
                             extra_tags='is-success')
        return super().form_valid(form)


class BillModelDeleteView(DeleteView):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'
    context_object_name = 'bill'
    template_name = 'django_ledger/bill_delete.html'

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


class BillModelMarkPaidView(View, SingleObjectMixin):
    slug_url_kwarg = 'bill_pk'
    slug_field = 'uuid'

    def get_queryset(self):
        return BillModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def post(self, request, *args, **kwargs):
        bill: BillModel = self.get_object()
        bill.paid = True
        bill.full_clean()
        bill.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             f'Successfully marked bill {bill.bill_number} as Paid.',
                             extra_tags='is-success')
        redirect_url = reverse('django_ledger:entity-dashboard',
                               kwargs={
                                   'entity_slug': self.kwargs['entity_slug']
                               })
        return HttpResponseRedirect(redirect_url)
