from django.contrib import messages
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import ArchiveIndexView, YearArchiveView, MonthArchiveView, DetailView, \
    RedirectView, FormView, CreateView, DeleteView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.closing_entry import ClosingEntryCreateForm, ClosingEntryUpdateForm
from django_ledger.models.closing_entry import ClosingEntryModel
from django_ledger.models.entity import EntityModel
from django_ledger.views import DjangoLedgerSecurityMixIn


class ClosingEntryModelViewQuerySetMixIn:
    queryset = None
    queryset_annotate_txs_count = False

    def get_queryset(self):
        if self.queryset is None:
            qs = ClosingEntryModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('entity_model', 'ledger_model')
            if self.queryset_annotate_txs_count:
                qs = qs.annotate(ce_txs_count=Count('closingentrytransactionmodel'))
            self.queryset = qs
        return super().get_queryset()


class ClosingEntryModelListView(DjangoLedgerSecurityMixIn,
                                ClosingEntryModelViewQuerySetMixIn,
                                ArchiveIndexView):
    template_name = 'django_ledger/closing_entry/closing_entry_list.html'
    date_field = 'closing_date'
    allow_future = False
    context_object_name = 'closing_entry_list'
    PAGE_TITLE = _('Closing Entry List')
    paginate_by = 10
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'file-icons:finaldraft'
    }
    queryset_annotate_txs_count = True


class ClosingEntryModelYearListView(YearArchiveView, ClosingEntryModelListView):
    paginate_by = 10
    make_object_list = True


class ClosingEntryModelMonthListView(MonthArchiveView, ClosingEntryModelListView):
    paginate_by = 10
    month_format = '%m'
    date_list_period = 'year'


class ClosingEntryModelCreateView(DjangoLedgerSecurityMixIn, ClosingEntryModelViewQuerySetMixIn, CreateView):
    template_name = 'django_ledger/closing_entry/closing_entry_create.html'
    form_class = ClosingEntryCreateForm
    PAGE_TITLE = _('Create Closing Entry')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'file-icons:finaldraft'
    }

    def get_initial(self):
        return {
            'closing_date': localdate()
        }

    def get_object(self, queryset=None):
        if not getattr(self, 'object'):
            entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user)
            entity_model = get_object_or_404(entity_model_qs, slug__exact=self.kwargs['entity_slug'])
            self.object = entity_model
        return self.object

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        entity_model = self.get_object()
        ctx['header_subtitle'] = entity_model.name
        return ctx

    def form_valid(self, form):
        closing_date = form.cleaned_data['closing_date']
        entity_model: EntityModel = self.get_object()
        ce_model, _ = entity_model.close_entity_books(closing_date=closing_date, force_update=True)
        self.ce_model = ce_model
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            viewname='django_ledger:closing-entry-detail',
            kwargs={
                'entity_slug': self.kwargs['entity_slug'],
                'closing_entry_pk': self.ce_model.uuid
            }
        )


class ClosingEntryModelDetailView(DjangoLedgerSecurityMixIn, ClosingEntryModelViewQuerySetMixIn, DetailView):
    template_name = 'django_ledger/closing_entry/closing_entry_detail.html'
    pk_url_kwarg = 'closing_entry_pk'
    context_object_name = 'closing_entry_model'
    extra_context = {
        'header_title': 'Closing Entry Detail',
        'header_subtitle_icon': 'file-icons:finaldraft'
    }
    queryset_annotate_txs_count = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        closing_entry_model = ctx['object']
        ctx['page_title'] = f'Closing Entry {closing_entry_model.closing_date}'
        closing_entry_txs_qs = closing_entry_model.closingentrytransactionmodel_set.all()
        ctx['closing_entry_txs_qs'] = closing_entry_txs_qs.select_related(
            'account_model', 'account_model__coa_model', 'unit_model')
        return ctx


class ClosingEntryModelUpdateView(DjangoLedgerSecurityMixIn, ClosingEntryModelViewQuerySetMixIn, UpdateView):
    template_name = 'django_ledger/closing_entry/closing_entry_update.html'
    pk_url_kwarg = 'closing_entry_pk'
    form_class = ClosingEntryUpdateForm
    context_object_name = 'closing_entry_model'
    queryset_annotate_txs_count = True
    extra_context = {
        'header_title': 'Closing Entry Detail',
        'header_subtitle_icon': 'file-icons:finaldraft'
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        closing_entry_model = ctx['object']
        ctx['page_title'] = f'Closing Entry {closing_entry_model.closing_date} Update'
        closing_entry_txs_qs = closing_entry_model.closingentrytransactionmodel_set.all()
        ctx['closing_entry_txs_qs'] = closing_entry_txs_qs.select_related(
            'account_model', 'account_model__coa_model', 'unit_model')
        return ctx

    def get_success_url(self):
        return reverse(
            viewname='django_ledger:closing-entry-detail',
            kwargs={
                'entity_slug': self.kwargs['entity_slug'],
                'closing_entry_pk': self.object.uuid
            }
        )

class ClosingEntryDeleteView(DjangoLedgerSecurityMixIn, ClosingEntryModelViewQuerySetMixIn, DeleteView):
    template_name = 'django_ledger/closing_entry/closing_entry_delete.html'
    pk_url_kwarg = 'closing_entry_pk'

    def get_success_url(self):
        return reverse(viewname='django_ledger:closing-entry-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


class ClosingEntryModelActionView(DjangoLedgerSecurityMixIn,
                                  RedirectView,
                                  ClosingEntryModelViewQuerySetMixIn,
                                  SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'closing_entry_pk'
    action_name = None
    commit = True

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:closing-entry-detail',
                       kwargs={
                           'entity_slug': kwargs['entity_slug'],
                           'closing_entry_pk': kwargs['closing_entry_pk']
                       })

    def get(self, request, *args, **kwargs):
        kwargs['user_model'] = self.request.user
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(ClosingEntryModelActionView, self).get(request, *args, **kwargs)
        closing_entry_model: ClosingEntryModel = self.get_object()

        try:
            getattr(closing_entry_model, self.action_name)(commit=self.commit, **kwargs)
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response
