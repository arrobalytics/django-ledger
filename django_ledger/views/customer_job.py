from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import ArchiveIndexView, CreateView, DetailView

from django_ledger.models import EntityModel
from django_ledger.models.customer_job import CustomerJobModel
from django_ledger.forms.customer_job import CreateCustomerJobModelForm
from django_ledger.views import LoginRequiredMixIn
from django.utils.translation import gettext_lazy as _


class CustomerJobModelListView(LoginRequiredMixIn, ArchiveIndexView):
    template_name = 'django_ledger/customer_job/customer_job_list.html'
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
        return CustomerJobModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_date_field(self):
        return 'created'


class CustomerJobModelCreateView(LoginRequiredMixIn, CreateView):
    PAGE_TITLE = _('Create Customer Job')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'eos-icons:job'
    }
    template_name = 'django_ledger/customer_job/customer_job_create.html'

    def get_form_class(self):
        return CreateCustomerJobModelForm

    def get_success_url(self):
        cj_model: CustomerJobModel = self.object
        return reverse('django_ledger:customer-job-detail',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'customer_job_pk': cj_model.uuid
                       })

    def form_valid(self, form):
        cj_model: CustomerJobModel = form.save(commit=False)

        # making sure the user as permissions on entity_model...
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user).only('uuid')
        entity_model: EntityModel = get_object_or_404(entity_model_qs, slug=self.kwargs['entity_slug'])
        cj_model.entity = entity_model

        return super(CustomerJobModelCreateView, self).form_valid(form)


class CustomerJobModelDetailView(LoginRequiredMixIn, DetailView):
    pk_url_kwarg = 'customer_job_pk'
    template_name = 'django_ledger/customer_job/customer_job_detail.html'
    PAGE_TITLE = _('Customer Job Detail')
    context_object_name = 'customer_job'

    def get_context_data(self, **kwargs):
        context = super(CustomerJobModelDetailView, self).get_context_data(**kwargs)
        cj_model: CustomerJobModel = self.object
        context['page_title'] = self.PAGE_TITLE,
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = cj_model.title
        context['header_subtitle_icon'] = 'eos-icons:job'
        return context

    def get_queryset(self):
        return CustomerJobModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).select_related('entity')
