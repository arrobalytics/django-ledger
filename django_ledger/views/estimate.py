from django.contrib import messages
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ArchiveIndexView, CreateView, DetailView, UpdateView, RedirectView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.estimate import (EstimateModelCreateForm, EstimateModelUpdateForm,
                                          CanEditEstimateItemModelFormset, ReadOnlyEstimateItemModelFormset)
from django_ledger.models import EntityModel, ItemThroughModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.views import LoginRequiredMixIn


class EstimateModelListView(LoginRequiredMixIn, ArchiveIndexView):
    template_name = 'django_ledger/customer_estimate/customer_estimate_list.html'
    context_object_name = 'ce_list'
    PAGE_TITLE = _('Customer Estimates')
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
        return EstimateModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('customer')

    def get_date_field(self):
        return 'created'


class EstimateModelCreateView(LoginRequiredMixIn, CreateView):
    PAGE_TITLE = _('Create Customer Estimate')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'eos-icons:job'
    }
    template_name = 'django_ledger/customer_estimate/customer_estimate_create.html'

    def get_form_class(self):
        return EstimateModelCreateForm

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        return form_class(entity_slug=self.kwargs['entity_slug'],
                          user_model=self.request.user,
                          **self.get_form_kwargs())

    def get_success_url(self):
        cj_model: EstimateModel = self.object
        return reverse('django_ledger:customer-estimate-detail',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'ce_pk': cj_model.uuid
                       })

    def form_valid(self, form):
        cj_model: EstimateModel = form.save(commit=False)

        # making sure the user as permissions on entity_model...
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user).only('uuid')
        entity_model: EntityModel = get_object_or_404(entity_model_qs, slug=self.kwargs['entity_slug'])
        cj_model.entity = entity_model

        return super(EstimateModelCreateView, self).form_valid(form)


class EstimateModelDetailView(LoginRequiredMixIn, DetailView):
    pk_url_kwarg = 'ce_pk'
    template_name = 'django_ledger/customer_estimate/customer_estimate_detail.html'
    PAGE_TITLE = _('Customer Estimate Detail')
    context_object_name = 'estimate_model'
    extra_context = {
        'hide_menu': True
    }
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        context = super(EstimateModelDetailView, self).get_context_data(**kwargs)
        ce_model: EstimateModel = self.object
        context['page_title'] = self.PAGE_TITLE,
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = ce_model.estimate_number
        context['header_subtitle_icon'] = 'eos-icons:job'
        context['customer_job_item_list'] = ce_model.itemthroughmodel_set.all()

        # PO Model Queryset...
        context['estimate_po_model_queryset'] = ce_model.purchaseordermodel_set.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ) if ce_model.is_approved() else ce_model.purchaseordermodel_set.none()

        return context

    def get_queryset(self):
        return EstimateModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('customer')


class EstimateModelUpdateView(LoginRequiredMixIn, UpdateView):
    template_name = 'django_ledger/customer_estimate/customer_estimate_update.html'
    pk_url_kwarg = 'ce_pk'
    context_object_name = 'customer_estimate'
    PAGE_TITLE = _('Customer Estimate Update')
    http_method_names = ['get', 'post']

    action_update_items = False

    def get_form_class(self):
        return EstimateModelUpdateForm

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        return form_class(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_context_data(self, item_formset: CanEditEstimateItemModelFormset = None, **kwargs):
        context = super(EstimateModelUpdateView, self).get_context_data(**kwargs)
        cj_model: EstimateModel = self.object

        context['page_title'] = self.PAGE_TITLE,
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = cj_model.title
        context['header_subtitle_icon'] = 'eos-icons:job'

        if not item_formset:
            item_through_qs, aggregate_data = cj_model.get_itemthrough_data()
        else:
            item_through_qs, aggregate_data = cj_model.get_itemthrough_data(
                queryset=item_formset.queryset
            )

        if cj_model.can_update_items():
            item_formset = CanEditEstimateItemModelFormset(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                customer_job_model=cj_model,
                queryset=item_through_qs
            )
        else:
            item_formset = ReadOnlyEstimateItemModelFormset(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user,
                customer_job_model=cj_model,
                queryset=item_through_qs
            )

        context['customer_job_item_list'] = item_through_qs
        context['revenue_estimate'] = aggregate_data['revenue_estimate']
        context['cost_estimate'] = aggregate_data['cost_estimate']
        context['cj_formset'] = item_formset
        return context

    def get_queryset(self):
        return EstimateModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('customer')

    def get_success_url(self):
        return reverse('django_ledger:customer-estimate-detail',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'ce_pk': self.kwargs['ce_pk']
                       })

    def get(self, request, entity_slug, ce_pk, *args, **kwargs):
        response = super(EstimateModelUpdateView, self).get(request, *args, **kwargs)

        # this action can only be used via POST request...
        if self.action_update_items:
            return HttpResponseBadRequest()

        return response

    def post(self, request, entity_slug, ce_pk, *args, **kwargs):
        response = super(EstimateModelUpdateView, self).post(request, *args, **kwargs)
        cj_model: EstimateModel = self.object

        if self.action_update_items:
            item_formset: CanEditEstimateItemModelFormset = CanEditEstimateItemModelFormset(request.POST,
                                                                                            user_model=self.request.user,
                                                                                            customer_job_model=cj_model,
                                                                                            entity_slug=entity_slug)
            if item_formset.is_valid():
                if item_formset.has_changed():
                    cleaned_data = [d for d in item_formset.cleaned_data if d]
                    cj_items = item_formset.save(commit=False)
                    cj_model_qs = EstimateModel.objects.for_entity(user_model=self.request.user,
                                                                   entity_slug=entity_slug)
                    cj_model: EstimateModel = get_object_or_404(cj_model_qs, uuid__exact=ce_pk)
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
                                         message=f'Customer estimate items saved.',
                                         level=messages.SUCCESS,
                                         extra_tags='is-success')

                    return HttpResponseRedirect(reverse('django_ledger:customer-estimate-update',
                                                        kwargs={
                                                            'entity_slug': entity_slug,
                                                            'ce_pk': ce_pk
                                                        }))


            else:
                context = self.get_context_data(item_formset=item_formset)
                return self.render_to_response(context=context)

        return response


# ---- ACTION VIEWS ----
class BaseEstimateActionView(LoginRequiredMixIn, RedirectView, SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'ce_pk'
    action_name = None
    commit = True

    def get_queryset(self):
        return EstimateModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_redirect_url(self, entity_slug, ce_pk, *args, **kwargs):
        return reverse('django_ledger:customer-estimate-update',
                       kwargs={
                           'entity_slug': entity_slug,
                           'ce_pk': ce_pk
                       })

    def get(self, request, *args, **kwargs):
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(BaseEstimateActionView, self).get(request, *args, **kwargs)
        ce_model: EstimateModel = self.get_object()

        try:
            getattr(ce_model, self.action_name)(commit=self.commit)
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response


class EstimateActionMarkAsDraftView(BaseEstimateActionView):
    action_name = 'mark_as_draft'


class EstimateActionMarkAsReviewView(BaseEstimateActionView):
    action_name = 'mark_as_review'


class EstimateActionMarkAsApprovedView(BaseEstimateActionView):
    action_name = 'mark_as_approved'


class EstimateActionMarkAsCompletedView(BaseEstimateActionView):
    action_name = 'mark_as_completed'


class EstimateActionMarkAsCanceledView(BaseEstimateActionView):
    action_name = 'mark_as_canceled'
