from datetime import datetime, timedelta
from random import randint

from django.urls import reverse
from django.utils.timezone import make_aware
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView

from django_ledger.forms.app_filters import AsOfDateFilterForm, EntityFilterForm
from django_ledger.forms.entity import EntityModelUpdateForm, EntityModelCreateForm
from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.utils import (
    get_date_filter_session_key, get_default_entity_session_key,
    populate_default_coa, generate_sample_data
)


# Entity Views ----
class EntityModelListView(ListView):
    template_name = 'django_ledger/entitiy_list.html'
    context_object_name = 'entities'
    PAGE_TITLE = _('My Entities')
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }

    def get_queryset(self):
        return EntityModel.objects.for_user(
            user_model=self.request.user)


class EntityModelDashboardView(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/entity_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entity = self.object
        context['page_title'] = entity.name
        context['header_title'] = _('Dashboard') + ': ' + entity.name

        session_date_filter_key = get_date_filter_session_key(entity.slug)
        date_filter = self.request.session.get(session_date_filter_key)
        date_filter = datetime.fromisoformat(date_filter) if date_filter else now()

        context['pnl_chart_id'] = f'djetler-pnl-chart-{randint(10000, 99999)}'
        context['payables_chart_id'] = f'djetler-payables-chart-{randint(10000, 99999)}'
        context['receivables_chart_id'] = f'djetler-receivables-chart-{randint(10000, 99999)}'

        # DIGEST PHASE ---
        by_period = self.request.GET.get('by_period')
        digest = entity.digest(user_model=self.request.user,
                               as_of=date_filter,
                               by_period=True if by_period else False,
                               process_ratios=True,
                               process_roles=True,
                               process_groups=True)
        context.update(digest)
        context['date_filter'] = date_filter - timedelta(days=1)

        context['bills'] = BillModel.objects.for_entity_unpaid(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).order_by('due_date')

        context['invoices'] = InvoiceModel.objects.for_entity_unpaid(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).order_by('due_date')
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(
            user_model=self.request.user)


class EntityModelCreateView(CreateView):
    template_name = 'django_ledger/entity_create.html'
    form_class = EntityModelCreateForm
    PAGE_TITLE = _('Create Entity')
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }

    def get_success_url(self):
        return reverse('django_ledger:dashboard')

    def form_valid(self, form):
        user = self.request.user
        form.instance.admin = user
        entity = form.save()
        default_coa = form.cleaned_data.get('default_coa')
        if default_coa:
            populate_default_coa(entity_model=entity)
        self.object = entity
        return super().form_valid(form)


class EntityModelManageView(UpdateView):
    context_object_name = 'entity'
    template_name = 'django_ledger/entity_update.html'
    form_class = EntityModelUpdateForm
    slug_url_kwarg = 'entity_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Manage Entity: ') + self.object.name
        # context['header_title'] = _('Manage Entity: ') + self.object.name
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-list')

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user_model=self.request.user)


class EntityModelBalanceSheetView(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/balance_sheet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Balance Sheet') + ': ' + self.object.name
        context['header_title'] = context['page_title']
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user_model=self.request.user)


class EntityModelIncomeStatementView(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/income_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('income statement: ') + self.object.name
        context['header_title'] = _('income statement: ') + self.object.name
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user_model=self.request.user)


class SetDefaultEntityView(RedirectView):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        form = EntityFilterForm(request.POST, user_model=request.user)
        session_key = get_default_entity_session_key()
        if form.is_valid():
            entity_model = form.cleaned_data['entity_model']
            self.url = reverse('django_ledger:entity-detail',
                               kwargs={
                                   'entity_slug': entity_model.slug
                               })
            self.request.session[session_key] = str(entity_model.uuid)
        else:
            try:
                del self.request.session[session_key]
            finally:
                self.url = reverse('django_ledger:entity-list')
        return super().post(request, *args, **kwargs)


class SetDateView(RedirectView):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        entity_slug = kwargs['entity_slug']
        as_of_form = AsOfDateFilterForm(data=request.POST, form_id=None)
        next_url = request.GET['next']

        if as_of_form.is_valid():
            as_of_date = as_of_form.cleaned_data['date']
            as_of_dttm = datetime(
                year=as_of_date.year,
                month=as_of_date.month,
                day=as_of_date.day,
                hour=0)
            as_of_dttm += timedelta(days=1)
            aware_dttm = make_aware(as_of_dttm)
            new_dttm_filter = aware_dttm.isoformat()
            session_key = get_date_filter_session_key(entity_slug)
            request.session[session_key] = new_dttm_filter
        self.url = next_url
        return super().post(request, *args, **kwargs)


class GenerateSampleData(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:entity-detail',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            generate_sample_data(
                entity=self.kwargs['entity_slug'],
                start_dt=datetime(2020, 2, 1),
                user_model=self.request.user,
                days_fw=30 * 6
            )
        return super().get(request, *args, **kwargs)
