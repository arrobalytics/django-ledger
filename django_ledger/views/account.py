from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView, UpdateView, CreateView

from django_ledger.forms.account import AccountModelUpdateForm, AccountModelCreateForm
from django_ledger.models import ChartOfAccountModel, AccountModel


# Account Views ----
class AccountModelListView(ListView):
    template_name = 'django_ledger/account_list.html'
    context_object_name = 'accounts'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Entity Accounts')
        context['header_title'] = _('Entity Accounts')
        return context

    def get_queryset(self):
        return AccountModel.on_coa.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            coa_slug=self.kwargs['coa_slug']
        ).order_by('code')


class AccountModelUpdateView(UpdateView):
    context_object_name = 'account'
    pk_url_kwarg = 'account_pk'
    template_name = 'django_ledger/account_update.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Update Account')
        context['header_title'] = _(f'Update Account: {self.object.code} - {self.object.name}')
        return context

    def get_form(self, form_class=None):
        return AccountModelUpdateForm(coa_slug=self.kwargs['coa_slug'],
                                      entity_slug=self.kwargs['entity_slug'],
                                      user_model=self.request.user,
                                      **self.get_form_kwargs())

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        coa_slug = self.kwargs.get('coa_slug')
        return reverse('django_ledger:account-list',
                       kwargs={
                           'entity_slug': entity_slug,
                           'coa_slug': coa_slug,
                       })

    def get_queryset(self):
        return AccountModel.on_coa.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
            coa_slug=self.kwargs['coa_slug']
        )


class AccountModelCreateView(CreateView):
    template_name = 'django_ledger/account_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Create Account')
        context['header_title'] = _('Create Account')
        return context

    def get_form(self, form_class=None):
        return AccountModelCreateForm(
            coa_slug=self.kwargs['coa_slug'],
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        coa_model = ChartOfAccountModel.objects.for_entity(
            user_model=self.request.user,
            coa_slug=self.kwargs['coa_slug'],
            entity_slug=self.kwargs['entity_slug']
        ).get(slug__iexact=self.kwargs['coa_slug'])
        form.instance.coa = coa_model
        self.object = form.save()
        return super().form_valid(form)

    def get_queryset(self):
        return AccountModel.on_coa.for_user(
            user_model=self.request.user
        )

    def get_success_url(self):
        entity_slug = self.kwargs.get('entity_slug')
        coa_slug = self.kwargs.get('coa_slug')
        return reverse('django_ledger:account-list',
                       kwargs={
                           'entity_slug': entity_slug,
                           'coa_slug': coa_slug,
                       })
