from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView

from django_ledger.examples.quickstart import quickstart
from django_ledger.forms import ActivitySelectForm
from django_ledger.forms import EntityModelUpdateForm, EntityModelCreateForm, EntityModelDefaultForm
from django_ledger.models import EntityModel
from django_ledger.models.utils import populate_default_coa


# from django_ledger.models_abstracts.accounts import BS_ROLES, ACCOUNT_TERRITORY


# def txs_digest(tx: dict) -> dict:
#     tx['role_bs'] = BS_ROLES.get(tx['account__role'])
#     if tx['account__balance_type'] != tx['tx_type']:
#         tx['amount'] = -tx['amount']
#     if tx['account__balance_type'] != ACCOUNT_TERRITORY.get(tx['role_bs']):
#         tx['amount'] = -tx['amount']
#     return tx


# Entity Views ----
class EntityModelListView(ListView):
    template_name = 'django_ledger/entitiy_list.html'
    context_object_name = 'entities'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('my entities')
        context['header_title'] = _('my entities')
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user=self.request.user)


class EntityModelDetailVew(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/entity_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['header_title'] = _l('entity') + ': ' + self.object.name
        entity = self.object
        snapshot = entity.snapshot()
        context.update(snapshot)
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user=self.request.user)


class EntityModelCreateView(CreateView):
    template_name = 'django_ledger/entity_create.html'
    form_class = EntityModelCreateForm
    extra_context = {
        'header_title': _('create entity'),
        'page_title': _('create entity')
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _l('create entity')
        context['header_title'] = _l('create entity')
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-list')

    def form_valid(self, form):
        user = self.request.user
        if user.is_authenticated:
            form.instance.admin = user
            self.object = form.save()

            use_quickstart = form.cleaned_data.get('quickstart')
            if use_quickstart:
                quickstart(user_model=self.request.user,
                           entity_model=form.instance)

            create_coa = form.cleaned_data.get('populate_default_coa')
            if create_coa and not use_quickstart:
                populate_default_coa(entity_model=self.object)
        return super().form_valid(form)


class EntityModelUpdateView(UpdateView):
    context_object_name = 'entity'
    template_name = 'django_ledger/entity_update.html'
    form_class = EntityModelUpdateForm
    slug_url_kwarg = 'entity_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _l('update entity: ') + self.object.name
        context['header_title'] = _l('update entity: ') + self.object.name
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-list')

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user=self.request.user)


class EntityBalanceSheetView(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/balance_sheet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('balance sheet') + ': ' + self.object.name
        context['header_title'] = _('balance sheet') + ': ' + self.object.name
        context['activity_form'] = ActivitySelectForm()
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user=self.request.user)


class EntityIncomeStatementView(DetailView):
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
        return EntityModel.objects.for_user(user=self.request.user)


class SetDefaultEntityView(RedirectView):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        form = EntityModelDefaultForm(request.POST, user_model=request.user)
        if form.is_valid():
            entity_model = form.cleaned_data['entity_model']
            self.url = reverse('django_ledger:entity-detail',
                               kwargs={
                                   'entity_slug': entity_model.slug
                               })
            self.request.session['default_entity_id'] = entity_model.id
        return super().post(request, *args, **kwargs)
