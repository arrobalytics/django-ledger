from django.contrib import messages
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ArchiveIndexView, CreateView, DetailView, UpdateView, RedirectView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.customer_estimate import (CustomerEstimateCreateForm, CustomerEstimateModelUpdateForm,
                                                   CustomerEstimateItemFormset, CustomerEstimateItemFormsetReadOnly)
from django_ledger.models import EntityModel, ItemThroughModel
from django_ledger.models.customer_estimate import CustomerEstimateModel
from django_ledger.views import LoginRequiredMixIn


class CustomerJobModelListView(LoginRequiredMixIn, ArchiveIndexView):
    template_name = 'django_ledger/customer_estimate/customer_estimate_list.html'
    context_object_name = 'customer_job_list'
    PAGE_TITLE = _('Customer Jobs')
    date_field = 'created'
    paginate_by = 20
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'eos-icons:job'
    }

    def get_queryset(self):
        return CustomerEstimateModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('customer')

    def get_date_field(self):
        return 'created'


class CustomerJobModelCreateView(LoginRequiredMixIn, CreateView):
    PAGE_TITLE = _('Create Customer Estimate')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'eos-icons:job'
    }
    template_name = 'django_ledger/customer_estimate/customer_estimate_create.html'

    def get_form_class(self):
        return CustomerEstimateCreateForm

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        return form_class(entity_slug=self.kwargs['entity_slug'],
                          user_model=self.request.user,
                          **self.get_form_kwargs())

    def get_success_url(self):
        cj_model: CustomerEstimateModel = self.object
        return reverse('django_ledger:customer-estimate-detail',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'customer_job_pk': cj_model.uuid
                       })

    def form_valid(self, form):
        cj_model: CustomerEstimateModel = form.save(commit=False)

        # making sure the user as permissions on entity_model...
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user).only('uuid')
        entity_model: EntityModel = get_object_or_404(entity_model_qs, slug=self.kwargs['entity_slug'])
        cj_model.entity = entity_model

        return super(CustomerJobModelCreateView, self).form_valid(form)


class CustomerJobModelDetailView(LoginRequiredMixIn, DetailView):
    pk_url_kwarg = 'customer_job_pk'
    template_name = 'django_ledger/customer_estimate/customer_estimate_detail.html'
    PAGE_TITLE = _('Customer Estimate Detail')
    context_object_name = 'customer_job'
    extra_context = {
        'hide_menu': True
    }
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        context = super(CustomerJobModelDetailView, self).get_context_data(**kwargs)
        cj_model: CustomerEstimateModel = self.object
        context['page_title'] = self.PAGE_TITLE,
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = cj_model.estimate_number
        context['header_subtitle_icon'] = 'eos-icons:job'
        context['customer_job_item_list'] = cj_model.itemthroughmodel_set.all()
        return context

    def get_queryset(self):
        return CustomerEstimateModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('customer')


class CustomerJobModelUpdateView(LoginRequiredMixIn, UpdateView):
    template_name = 'django_ledger/customer_estimate/customer_estimate_update.html'
    pk_url_kwarg = 'customer_job_pk'
    context_object_name = 'customer_estimate'
    PAGE_TITLE = _('Customer Estimate Update')
    http_method_names = ['get', 'post']

    action_update_items = False

    def get_form_class(self):
        return CustomerEstimateModelUpdateForm

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        return form_class(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_context_data(self, item_formset: CustomerEstimateItemFormset = None, **kwargs):
        context = super(CustomerJobModelUpdateView, self).get_context_data(**kwargs)
        cj_model: CustomerEstimateModel = self.object

        context['page_title'] = self.PAGE_TITLE,
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = cj_model.title
        context['header_subtitle_icon'] = 'eos-icons:job'

        if not item_formset:
            item_through_qs, aggregate_data = cj_model.get_itemthrough_data()
            if cj_model.can_update_items():
                item_formset = CustomerEstimateItemFormset(
                    entity_slug=self.kwargs['entity_slug'],
                    user_model=self.request.user,
                    customer_job_model=cj_model,
                    queryset=item_through_qs
                )
            else:
                item_formset = CustomerEstimateItemFormsetReadOnly(
                    entity_slug=self.kwargs['entity_slug'],
                    user_model=self.request.user,
                    customer_job_model=cj_model,
                    queryset=item_through_qs
                )

        else:
            item_through_qs: ItemThroughModel = item_formset.queryset

        context['customer_job_item_list'] = item_through_qs
        context['revenue_estimate'] = aggregate_data['revenue_estimate']
        context['cost_estimate'] = aggregate_data['cost_estimate']
        context['cj_formset'] = item_formset
        return context

    def get_queryset(self):
        return CustomerEstimateModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('customer')

    def get_success_url(self):
        return reverse('django_ledger:customer-estimate-detail',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'customer_job_pk': self.kwargs['customer_job_pk']
                       })

    def get(self, request, entity_slug, customer_job_pk, *args, **kwargs):
        response = super(CustomerJobModelUpdateView, self).get(request, *args, **kwargs)

        # this action can only be used via POST request...
        if self.action_update_items:
            return HttpResponseBadRequest()

        return response

    def post(self, request, entity_slug, customer_job_pk, *args, **kwargs):
        response = super(CustomerJobModelUpdateView, self).post(request, *args, **kwargs)
        cj_model: CustomerEstimateModel = self.object

        if self.action_update_items:
            item_formset: CustomerEstimateItemFormset = CustomerEstimateItemFormset(request.POST,
                                                                                    user_model=self.request.user,
                                                                                    customer_job_model=cj_model,
                                                                                    entity_slug=entity_slug)
            if item_formset.is_valid():
                if item_formset.has_changed():
                    cleaned_data = [d for d in item_formset.cleaned_data if d]
                    cj_items = item_formset.save(commit=False)
                    cj_model_qs = CustomerEstimateModel.objects.for_entity(user_model=self.request.user,
                                                                           entity_slug=entity_slug)
                    cj_model: CustomerEstimateModel = get_object_or_404(cj_model_qs, uuid__exact=customer_job_pk)
                    entity_qs = EntityModel.objects.for_user(user_model=self.request.user)
                    entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)

                    for item in cj_items:
                        item.entity = entity_model
                        item.ce_model = cj_model

                    item_formset.save()

                    cj_model.update_state()
                    cj_model.clean()
                    cj_model.save(update_fields=[
                        'revenue_estimate',
                        'labor_estimate',
                        'equipment_estimate',
                        'material_estimate',
                        'other_estimate',
                        'updated'
                    ])

                    messages.add_message(request,
                                         message=f'Customer Job items saved.',
                                         level=messages.SUCCESS,
                                         extra_tags='is-success')

                    return HttpResponseRedirect(reverse('django_ledger:customer-estimate-update',
                                                        kwargs={
                                                            'entity_slug': entity_slug,
                                                            'customer_job_pk': customer_job_pk
                                                        }))


            else:
                context = self.get_context_data(item_formset=item_formset)
                return self.render_to_response(context=context)

        return response


# ---- ACTION VIEWS ----

class BaseCustomerEstimateActionView(LoginRequiredMixIn, RedirectView, SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'customer_job_pk'
    action_name = None
    commit = True

    def get_queryset(self):
        return CustomerEstimateModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_redirect_url(self, entity_slug, customer_job_pk, *args, **kwargs):
        return reverse('django_ledger:customer-estimate-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'customer_job_pk': customer_job_pk
                       })

    def get(self, request, *args, **kwargs):
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(BaseCustomerEstimateActionView, self).get(request, *args, **kwargs)
        ce_model: CustomerEstimateModel = self.get_object()

        try:
            getattr(ce_model, self.action_name)(commit=self.commit)
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response


class CustomerEstimateActionMarkAsDraftView(BaseCustomerEstimateActionView):
    action_name = 'mark_as_draft'


class CustomerEstimateActionMarkAsReviewView(BaseCustomerEstimateActionView):
    action_name = 'mark_as_review'


class CustomerEstimateActionMarkAsApprovedView(BaseCustomerEstimateActionView):
    action_name = 'mark_as_approved'


class CustomerEstimateActionMarkAsCompletedView(BaseCustomerEstimateActionView):
    action_name = 'mark_as_completed'


class CustomerEstimateActionMarkAsCanceledView(BaseCustomerEstimateActionView):
    action_name = 'mark_as_canceled'
