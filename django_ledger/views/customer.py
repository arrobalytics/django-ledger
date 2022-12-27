"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView

from django_ledger.forms.customer import CustomerModelForm
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class CustomerModelListView(DjangoLedgerSecurityMixIn,
                            ListView):
    template_name = 'django_ledger/customer/customer_list.html'
    PAGE_TITLE = _('Customer List')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'dashicons:businesswoman'
    }
    context_object_name = 'customers'

    def get_queryset(self):
        return CustomerModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).order_by('-updated')


class CustomerModelCreateView(DjangoLedgerSecurityMixIn,
                              CreateView):
    template_name = 'django_ledger/customer/customer_create.html'
    PAGE_TITLE = _('Create New Customer')
    form_class = CustomerModelForm
    context_object_name = 'customer'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'dashicons:businesswoman'
    }

    def get_queryset(self):
        return CustomerModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_success_url(self):
        return reverse('django_ledger:customer-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def form_valid(self, form):
        customer_model: CustomerModel = form.save(commit=False)
        entity_model = EntityModel.objects.for_user(
            user_model=self.request.user
        ).get(slug__exact=self.kwargs['entity_slug'])
        customer_model.entity_model = entity_model
        customer_model.save()
        return super().form_valid(form)


class CustomerModelUpdateView(DjangoLedgerSecurityMixIn,
                              UpdateView):
    template_name = 'django_ledger/customer/customer_update.html'
    PAGE_TITLE = _('Customer Update')
    form_class = CustomerModelForm
    context_object_name = 'customer'
    slug_url_kwarg = 'customer_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super(CustomerModelUpdateView, self).get_context_data(**kwargs)
        customer_model: CustomerModel = self.object
        context['page_title'] = self.PAGE_TITLE
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = customer_model.customer_number
        context['header_subtitle_icon'] = 'dashicons:businesswoman'
        return context

    def get_queryset(self):
        return CustomerModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_success_url(self):
        return reverse('django_ledger:customer-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

# todo: add CustomerDeleteView
