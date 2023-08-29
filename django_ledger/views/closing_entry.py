from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.views.generic import ArchiveIndexView, YearArchiveView, MonthArchiveView, CreateView

from django_ledger.forms.closing_entry import ClosingEntryCreateForm
from django_ledger.models.entity import EntityModel
from django_ledger.models.closing_entry import ClosingEntryModel
from django_ledger.views import DjangoLedgerSecurityMixIn
from django.utils.translation import gettext_lazy as _


class ClosingEntryModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            self.queryset = ClosingEntryModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('entity_model')
        return super().get_queryset()


class ClosingEntryModelListView(DjangoLedgerSecurityMixIn, ClosingEntryModelViewQuerySetMixIn, ArchiveIndexView):
    template_name = 'django_ledger/closing_entry/closing_entry_list.html'
    date_field = 'closing_date'
    allow_future = False
    context_object_name = 'closing_entry_list'
    PAGE_TITLE = _('Closing Entry List')
    paginate_by = 10
    paginate_orphans = 2
    allow_empty = False
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'file-icons:finaldraft'
    }


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
        closing_entry_model: ClosingEntryModel = form.save(commit=False)
        entity_model = self.get_object()
        closing_entry_model.entity_model = entity_model

        try:
            closing_entry_model.validate_constraints()
        except ValidationError as e:
            messages.add_message(self.request,
                                 level=messages.ERROR,
                                 extra_tags='is-danger',
                                 message=e.message_dict['__all__'])
            return self.render_to_response(
                context=self.get_context_data()
            )
        return super().form_valid(form=form)

    def get_success_url(self):
        return reverse(
            viewname='django_ledger:closing-entry-list',
            kwargs={
                'entity_slug': self.kwargs['entity_slug']
            }
        )
