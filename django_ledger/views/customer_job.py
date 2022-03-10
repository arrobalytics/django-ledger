from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import ArchiveIndexView, CreateView

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
    form_class = CreateCustomerJobModelForm

    def get_success_url(self):
        # todo: redirect to detail view once implemented...
        # cj_model = self.get_object()
        return reverse('django_ledger:customer-job-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def form_valid(self, form):
        cj_model: CustomerJobModel = form.save(commit=False)
        
        # making sure the user as permissions on entity_model...
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user).only('uuid')
        entity_model: EntityModel = get_object_or_404(entity_model_qs, slug=self.kwargs['entity_slug'])
        cj_model.entity = entity_model
        
        return super(CustomerJobModelCreateView, self).form_valid(form)
