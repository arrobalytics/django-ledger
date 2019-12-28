from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView, UpdateView, CreateView

from django_ledger.forms import AccountModelUpdateForm, AccountModelCreateForm
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
        qs = AccountModel.on_coa.for_user(user=self.request.user)
        return qs.filter(coa__entity__slug=self.kwargs['entity_slug']).order_by('code')


class AccountModelUpdateView(UpdateView):
    context_object_name = 'account'
    pk_url_kwarg = 'account_pk'
    template_name = 'django_ledger/account_update.html'
    form_class = AccountModelUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Update Account')
        context['header_title'] = _(f'Update Account: {self.object.code} - {self.object.name}')
        return context

    def get_success_url(self):
        return reverse('django_ledger:account-list',
                       kwargs={
                           'coa_slug': self.kwargs['coa_slug'],
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_queryset(self):
        return AccountModel.on_coa.for_user(
            user=self.request.user
        ).filter(
            Q(coa__slug__exact=self.kwargs['coa_slug']) &
            Q(coa__entity__slug__exact=self.kwargs['entity_slug'])
        )


class AccountModelCreateView(CreateView):
    template_name = 'django_ledger/account_create.html'
    form_class = AccountModelCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Create Account')
        context['header_title'] = _('Create Account')
        return context

    def get_form(self, form_class=None):
        return AccountModelCreateForm(coa_slug=self.kwargs['coa_slug'],
                                      entity_slug=self.kwargs['entity_slug'],
                                      **self.get_form_kwargs())

    def form_valid(self, form):
        coa_model = ChartOfAccountModel.objects.for_user(
            user=self.request.user
        ).filter(entity__slug=self.kwargs['entity_slug']).get(
            slug=self.kwargs['coa_slug'])

        form.instance.coa = coa_model
        self.object = form.save()
        return super().form_valid(form)

    def get_queryset(self):
        return AccountModel.on_coa.for_user(
            user=self.request.user
        )

    def get_success_url(self):
        return reverse('django_ledger:coa-detail',
                       kwargs={
                           'coa_slug': self.object.coa.slug,
                           'entity_slug': self.object.coa.entity.slug
                       })

