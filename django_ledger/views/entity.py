from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView

from django_ledger.examples.quickstart import quickstart
from django_ledger.forms.app_filters import EndDateFilterForm, EntityFilterForm
from django_ledger.forms.entity import EntityModelUpdateForm, EntityModelCreateForm
from django_ledger.models.entity import EntityModel
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
        return EntityModel.objects.for_user(user_model=self.request.user)


class EntityModelDetailVew(DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/entity_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['header_title'] = _('entity') + ': ' + self.object.name
        entity = self.object
        session_date_filter_key = get_date_filter_session_key(entity.slug)
        date_filter = self.request.session.get(session_date_filter_key)

        # entity_slug = self.kwargs.get('entity_slug')
        user = self.request.user

        digest = entity.digest(user_model=user,
                               as_of=date_filter,
                               process_ratios=True,
                               process_roles=True,
                               process_groups=True)
        context.update(digest)
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user_model=self.request.user)


class EntityModelCreateView(CreateView):
    template_name = 'django_ledger/entity_create.html'
    form_class = EntityModelCreateForm
    extra_context = {
        'header_title': _('create entity'),
        'page_title': _('create entity')
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('create entity')
        context['header_title'] = _('create entity')
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
        context['page_title'] = _('update entity: ') + self.object.name
        context['header_title'] = _('update entity: ') + self.object.name
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
        context['page_title'] = _('balance sheet') + ': ' + self.object.name
        context['header_title'] = _('balance sheet') + ': ' + self.object.name
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
        as_of_form = EndDateFilterForm(data=request.POST, form_id=None)
        next_url = request.GET['next']

        if as_of_form.is_valid():
            session_item = get_date_filter_session_key(entity_slug)
            new_date_filter = as_of_form.cleaned_data['date'].strftime('%Y-%m-%d')
            request.session[session_item] = new_date_filter

        self.url = next_url
        return super().post(request, *args, **kwargs)
