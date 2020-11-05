from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView, UpdateView, CreateView, DetailView

from django_ledger.forms.account import AccountModelUpdateForm, AccountModelCreateForm
from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa import ChartOfAccountModel


# Account Views ----
class AccountModelListView(ListView):
    template_name = 'django_ledger/account_list.html'
    context_object_name = 'accounts'
    extra_context = {
        'page_title': _('Entity Accounts'),
        'header_title': _('Entity Accounts')
    }

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['asset_accounts'] = (a for a in qs if a.role_bs == 'assets')
        context['liability_accounts'] = (a for a in qs if a.role_bs == 'liabilities')
        context['equity_accounts'] = (a for a in qs if a.role_bs == 'equity')
        return context

    def get_queryset(self):
        return AccountModel.on_coa.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
        ).order_by('code')


class AccountModelUpdateView(UpdateView):
    context_object_name = 'account'
    template_name = 'django_ledger/account_update.html'
    slug_url_kwarg = 'account_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Update Account')
        context['header_title'] = _(f'Update Account: {self.object.code} - {self.object.name}')
        return context

    def get_form(self, form_class=None):
        return AccountModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        entity_slug = self.kwargs['entity_slug']
        return reverse('django_ledger:account-list',
                       kwargs={
                           'entity_slug': entity_slug,
                       })

    def get_queryset(self):
        return AccountModel.on_coa.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
        )


class AccountModelDetailView(DetailView):
    context_object_name = 'account'
    template_name = 'django_ledger/account_detail.html'
    slug_url_kwarg = 'account_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = self.object
        context['transactions'] = account.txs.all().order_by('-journal_entry__date')
        return context

    def get_queryset(self):
        return AccountModel.on_coa.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
        ).prefetch_related('txs')


class AccountModelCreateView(CreateView):
    template_name = 'django_ledger/account_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Create Account')
        context['header_title'] = _('Create Account')
        return context

    def get_initial(self):
        return {
            'coa': ChartOfAccountModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).get(entity__slug__exact=self.kwargs['entity_slug'])
        }

    def get_form(self, form_class=None):
        return AccountModelCreateForm(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        coa_model = ChartOfAccountModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).get(entity__slug__exact=self.kwargs['entity_slug'])
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
                       })
