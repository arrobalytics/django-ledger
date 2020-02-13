from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView

from django_ledger.examples.quickstart import quickstart
from django_ledger.forms import EntityModelUpdateForm, EntityModelCreateForm
from django_ledger.forms.app_filters import EndDateFilterForm, EntityFilterForm
from django_ledger.models import EntityModel
from django_ledger.models.utils import get_date_filter_session_key, get_default_entity_session_key
from django_ledger.models.utils import populate_default_coa


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
        session_date_filter_key = get_date_filter_session_key(entity.slug)
        date_filter = self.request.session.get(session_date_filter_key)
        digest = entity.digest(as_of=date_filter, ratios=True)
        context.update(digest)
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
        form = EntityFilterForm(request.POST, user_model=request.user)
        if form.is_valid():
            entity_model = form.cleaned_data['entity_model']
            # todo: redirect to same origin view on selected entity.
            self.url = reverse('django_ledger:entity-detail',
                               kwargs={
                                   'entity_slug': entity_model.slug
                               })
            session_key = get_default_entity_session_key()
            self.request.session[session_key] = entity_model.id
        return super().post(request, *args, **kwargs)


class SetDateView(RedirectView):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        entity_slug = kwargs['entity_slug']
        as_of_form = EndDateFilterForm(data=request.POST, form_id=None)
        next_url = request.GET['next']

        if as_of_form.is_valid():
            session_item = get_date_filter_session_key(entity_slug)
            new_date_filter = as_of_form.cleaned_data['date'].strftime('%Y-%m-%d')
            request.session[session_item] = new_date_filter

        self.url = next_url
        return super().post(request, *args, **kwargs)
