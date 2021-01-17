"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from calendar import month_abbr
from random import randint

from django import template
from django.urls import reverse
from django.utils.formats import number_format

from django_ledger import __version__
from django_ledger.forms.app_filters import EntityFilterForm, AsOfDateFilterForm, ActivityFilterForm
from django_ledger.forms.feedback import BugReportForm, RequestNewFeatureForm
from django_ledger.models import TransactionModel, BillModel, InvoiceModel
from django_ledger.models.journalentry import validate_activity
from django_ledger.settings import (
    DJANGO_LEDGER_FINANCIAL_ANALYSIS, DJANGO_LEDGER_CURRENCY_SYMBOL,
    DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL)
from django_ledger.utils import get_default_entity_session_key, get_end_date_from_session

register = template.Library()


@register.simple_tag(name='current_version')
def current_version():
    return __version__


@register.simple_tag(name='currency_symbol')
def currency_symbol(spaced: bool = False):
    if spaced or DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL:
        return f'{DJANGO_LEDGER_CURRENCY_SYMBOL} '
    return DJANGO_LEDGER_CURRENCY_SYMBOL


@register.filter(name='currency_format')
def currency_format(value):
    if value:
        return number_format(value, decimal_pos=2, use_l10n=True, force_grouping=True)
    return 0


@register.filter(name='percentage')
def percentage(value):
    if value:
        return '{0:,.2f}%'.format(value * 100)


@register.filter(name='reverse_sing')
def reverse_sign(value: float):
    if value:
        return -value
    return 0


@register.filter(name='last_four')
def last_four(value: str):
    if value:
        return '*' + value[-4:]
    return ''


@register.inclusion_tag('django_ledger/tags/icon.html')
def icon(icon_name, size):
    return {
        'icon': icon_name,
        'size': size
    }


@register.inclusion_tag('django_ledger/tags/balance_sheet.html', takes_context=True)
def balance_sheet_table(context, ledger_or_entity, end_date):
    user_model = context['user']
    activity = context['request'].GET.get('activity')
    activity = validate_activity(activity, raise_404=True)
    return ledger_or_entity.digest(
        activity=activity,
        user_model=user_model,
        equity_only=False,
        to_date=end_date,
        process_groups=True)


@register.inclusion_tag('django_ledger/tags/income_statement.html', takes_context=True)
def income_statement_table(context, ledger_or_entity, start_date, end_date):
    user_model = context['user']
    activity = context['request'].GET.get('activity')
    activity = validate_activity(activity, raise_404=True)
    return ledger_or_entity.digest(
        activity=activity,
        user_model=user_model,
        from_date=start_date,
        to_date=end_date,
        equity_only=True,
        process_groups=True)


@register.inclusion_tag('django_ledger/tags/bank_accounts_table.html', takes_context=True)
def bank_account_table(context, bank_account_qs):
    entity_slug = context['view'].kwargs['entity_slug']
    return {
        'bank_account_qs': bank_account_qs,
        'entity_slug': entity_slug
    }


@register.inclusion_tag('django_ledger/tags/data_import_job_list_table.html', takes_context=True)
def data_import_job_list_table(context):
    return context


@register.inclusion_tag('django_ledger/tags/data_import_job_txs_table.html', takes_context=True)
def data_import_job_txs_pending(context):
    return context


@register.inclusion_tag('django_ledger/tags/data_import_job_txs_imported.html', takes_context=True)
def data_import_job_txs_imported(context):
    return context


@register.inclusion_tag('django_ledger/tags/jes_table.html', takes_context=True)
def jes_table(context):
    return {
        'jes': context['journal_entries'],
        'entity_slug': context['view'].kwargs['entity_slug'],
        'ledger_pk': context['view'].kwargs['ledger_pk']
    }


@register.inclusion_tag('django_ledger/tags/txs_table.html')
def journal_entry_txs_table(journal_entry_model):
    txs_queryset = journal_entry_model.txs.all()
    total_credits = sum(tx.amount for tx in txs_queryset if tx.tx_type == 'credit')
    total_debits = sum(tx.amount for tx in txs_queryset if tx.tx_type == 'debit')
    return {
        'txs': txs_queryset,
        'total_debits': total_debits,
        'total_credits': total_credits
    }


@register.inclusion_tag('django_ledger/tags/txs_table.html', takes_context=True)
def bill_txs_table(context, bill_model: BillModel):
    txs_queryset = TransactionModel.objects.for_bill(
        bill_pk=bill_model.uuid,
        user_model=context['request'].user,
        entity_slug=context['view'].kwargs['entity_slug']
    ).select_related('journal_entry').order_by('-journal_entry__date')
    total_credits = sum(tx.amount for tx in txs_queryset if tx.tx_type == 'credit')
    total_debits = sum(tx.amount for tx in txs_queryset if tx.tx_type == 'debit')
    return {
        'txs': txs_queryset,
        'total_debits': total_debits,
        'total_credits': total_credits
    }


@register.inclusion_tag('django_ledger/tags/txs_table.html', takes_context=True)
def invoice_txs_table(context, invoice_model: InvoiceModel):
    txs_queryset = TransactionModel.objects.for_invoice(
        invoice_pk=invoice_model.uuid,
        user_model=context['request'].user,
        entity_slug=context['view'].kwargs['entity_slug']
    ).select_related('journal_entry').order_by('-journal_entry__date')
    total_credits = sum(tx.amount for tx in txs_queryset if tx.tx_type == 'credit')
    total_debits = sum(tx.amount for tx in txs_queryset if tx.tx_type == 'debit')
    return {
        'txs': txs_queryset,
        'total_debits': total_debits,
        'total_credits': total_credits
    }


@register.inclusion_tag('django_ledger/tags/ledgers_table.html', takes_context=True)
def ledgers_table(context):
    return {
        'ledgers': context['ledgers'],
        'entity_slug': context['view'].kwargs['entity_slug'],
    }


@register.inclusion_tag('django_ledger/tags/invoice_table.html', takes_context=True)
def invoice_table(context):
    return {
        'invoices': context['invoices'],
        'entity_slug': context['view'].kwargs['entity_slug']
    }


@register.inclusion_tag('django_ledger/tags/bill_table.html', takes_context=True)
def bill_table(context):
    return {
        'bills': context['bills'],
        'entity_slug': context['view'].kwargs['entity_slug']
    }


@register.inclusion_tag('django_ledger/tags/accounts_table.html', takes_context=True)
def accounts_table(context, accounts_qs, title=None):
    return {
        'accounts': accounts_qs,
        'title': title,
        'entity_slug': context['view'].kwargs['entity_slug'],
    }


@register.inclusion_tag('django_ledger/tags/customer_table.html', takes_context=True)
def customer_table(context):
    return context


@register.inclusion_tag('django_ledger/tags/vendor_table.html', takes_context=True)
def vendor_table(context):
    return context


@register.inclusion_tag('django_ledger/tags/account_txs_table.html', takes_context=True)
def account_txs_table(context, txs_qs):
    return {
        'transactions': txs_qs,
        'total_credits': sum(tx.amount for tx in txs_qs if tx.tx_type == 'credit'),
        'total_debits': sum(tx.amount for tx in txs_qs if tx.tx_type == 'debit'),
        'entity_slug': context['view'].kwargs['entity_slug'],
        'account_pk': context['view'].kwargs['account_pk']
    }


@register.inclusion_tag('django_ledger/tags/breadcrumbs.html', takes_context=True)
def nav_breadcrumbs(context):
    entity_slug = context['view'].kwargs.get('entity_slug')
    coa_slug = context['view'].kwargs.get('coa_slug')
    ledger_pk = context['view'].kwargs.get('entity_slug')
    account_pk = context['view'].kwargs.get('account_pk')
    return {
        'entity_slug': entity_slug,
        'coa_slug': coa_slug,
        'ledger_pk': ledger_pk,
        'account_pk': account_pk
    }


@register.inclusion_tag('django_ledger/tags/default_entity.html', takes_context=True)
def default_entity(context):
    user = context['user']
    session_key = get_default_entity_session_key()
    session = context['request'].session
    session_entity_data = session.get(session_key)
    identity = randint(0, 1000000)
    try:
        entity_uuid = session_entity_data['entity_uuid']
        default_entity_form = EntityFilterForm(
            user_model=user,
            form_id=identity,
            current_entity_uuid=entity_uuid
        )
    except TypeError or KeyError:
        default_entity_form = EntityFilterForm(
            user_model=user,
            form_id=identity,
        )

    return {
        'default_entity_form': default_entity_form,
        'form_id': identity,
    }


@register.simple_tag(takes_context=True)
def session_entity_name(context, request=None):
    session_key = get_default_entity_session_key()
    if not request:
        request = context['request']
    session = request.session
    return session.get(session_key)['entity_name']


# todo: rename template to activity_form_filter.
@register.inclusion_tag('django_ledger/tags/activity_form.html', takes_context=True)
def activity_filter(context):
    request = context['request']
    activity = request.GET.get('activity')
    if activity:
        activity_form = ActivityFilterForm(initial={
            'activity': activity
        })
    else:
        activity_form = ActivityFilterForm()

    return {
        'activity_form': activity_form,
        'form_path': context['request'].path
    }


@register.inclusion_tag('django_ledger/tags/date_filter.html', takes_context=True)
def date_filter_form(context, inline=False):
    entity_slug = context['view'].kwargs.get('entity_slug')
    end_date = get_end_date_from_session(entity_slug, context['request'])
    identity = randint(0, 1000000)
    if entity_slug:
        form = AsOfDateFilterForm(form_id=identity, initial={
            'entity_slug': context['view'].kwargs['entity_slug'],
            'date': end_date
        })
        next_url = context['request'].path
        return {
            'date_form': form,
            'form_id': identity,
            'entity_slug': entity_slug,
            'date_filter': end_date,
            'next': next_url,
            'inline': inline
        }


@register.simple_tag(takes_context=True)
def get_current_end_date_filter(context):
    entity_slug = context['view'].kwargs.get('entity_slug')
    return get_end_date_from_session(entity_slug, context['request'])


@register.inclusion_tag('django_ledger/tags/chart_container.html')
def chart_container(chart_id, endpoint=None):
    return {
        'chart_id': chart_id,
        'endpoint': endpoint
    }


@register.inclusion_tag('django_ledger/tags/modals.html', takes_context=True)
def mark_as_paid(context, model, entity_slug: str = None):
    if not entity_slug:
        entity_slug = context['view'].kwargs['entity_slug']
    action_url = model.get_mark_paid_url(entity_slug=entity_slug)
    return {
        'object': model,
        'action_url': action_url,
        'message': f'Do you want to mark {model.__class__._meta.verbose_name} {model.get_document_id()} as paid?'
    }


@register.simple_tag
def fin_ratio_max_value(ratio: str):
    params = DJANGO_LEDGER_FINANCIAL_ANALYSIS['ratios'][ratio]['ranges']
    return params['healthy']


@register.filter
def fin_ratio_threshold_class(value, ratio):
    if value:
        params = DJANGO_LEDGER_FINANCIAL_ANALYSIS['ratios'][ratio]
        ranges = params['ranges']

        if params['good_incremental']:
            if value <= ranges['critical']:
                return 'is-danger'
            elif value <= ranges['warning']:
                return 'is-warning'
            elif value <= ranges['watch']:
                return 'is-primary'
            return 'is-success'
        else:
            if value >= ranges['critical']:
                return 'is-danger'
            elif value >= ranges['warning']:
                return 'is-warning'
            elif value >= ranges['watch']:
                return 'is-primary'
            return 'is-success'


@register.inclusion_tag('django_ledger/tags/feedback_button.html', takes_context=True)
def feedback_button(context, button_size_class: str = 'is-small', color_class: str = 'is-success', icon_id: str = None):
    bug_modal_html_id = f'djl-bug-button-{randint(10000, 99999)}'
    feature_modal_html_id = f'djl-feature-button-{randint(10000, 99999)}'
    bug_form = BugReportForm()
    feature_form = RequestNewFeatureForm()
    next_url = context['request'].path
    return {
        'icon_id': icon_id,
        'bug_modal_html_id': bug_modal_html_id,
        'feature_modal_html_id': feature_modal_html_id,
        'button_size_class': button_size_class,
        'color_class': color_class,
        'bug_form': bug_form,
        'feature_form': feature_form,
        'next_url': next_url
    }


@register.inclusion_tag('django_ledger/tags/period_navigator.html', takes_context=True)
def period_navigation(context, base_url: str):
    KWARGS = dict()
    KWARGS['entity_slug'] = context['view'].kwargs['entity_slug']
    KWARGS['year'] = context.get('year')

    if context['view'].kwargs.get('ledger_pk'):
        KWARGS['ledger_pk'] = context['view'].kwargs.get('ledger_pk')

    if context['view'].kwargs.get('account_pk'):
        KWARGS['account_pk'] = context['view'].kwargs.get('account_pk')

    ctx = dict()
    ctx['year'] = context['year']
    ctx['has_year'] = context.get('has_year')
    ctx['has_quarter'] = context.get('has_quarter')
    ctx['has_month'] = context.get('has_month')
    ctx['previous_year'] = context['previous_year']
    ctx['previous_year_url'] = reverse(f'django_ledger:{base_url}-year', kwargs=KWARGS)
    ctx['next_year'] = context['next_year']
    ctx['next_year_url'] = reverse(f'django_ledger:{base_url}-year', kwargs=KWARGS)

    quarter_urls = list()
    ctx['quarter'] = context.get('quarter')
    for Q in range(1, 5):
        KWARGS['quarter'] = Q
        quarter_urls.append({
            'url': reverse(f'django_ledger:{base_url}-quarter', kwargs=KWARGS),
            'quarter': Q,
            'quarter_name': f'Q{Q}'
        })
    del KWARGS['quarter']
    ctx['quarter_urls'] = quarter_urls

    month_urls = list()
    ctx['month'] = context.get('month')
    for M in range(1, 13):
        KWARGS['month'] = M
        month_urls.append({
            'url': reverse(f'django_ledger:{base_url}-month', kwargs=KWARGS),
            'month': M,
            'month_abbr': month_abbr[M]
        })
    ctx['month_urls'] = month_urls

    ctx['start_date'] = context['start_date']
    ctx['end_date'] = context['end_date']

    ctx.update(KWARGS)

    return ctx


@register.inclusion_tag('django_ledger/tags/menu.html', takes_context=True)
def navigation_menu(context, style):
    ENTITY_SLUG = context['view'].kwargs.get('entity_slug')

    ctx = dict()
    ctx['style'] = style
    if ENTITY_SLUG:
        ctx['entity_slug'] = ENTITY_SLUG
        nav_menu_links = [
            {
                'type': 'link',
                'title': 'Entity Dashboard',
                'url': reverse('django_ledger:entity-detail', kwargs={'entity_slug': ENTITY_SLUG})
            },
            {
                'type': 'links',
                'title': 'Your Lists',
                'links': [
                    {
                        'type': 'link',
                        'title': 'Vendors',
                        'url': reverse('django_ledger:vendor-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Customers',
                        'url': reverse('django_ledger:customer-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Bank Accounts',
                        'url': reverse('django_ledger:bank-account-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Bills',
                        'url': reverse('django_ledger:bill-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Invoices',
                        'url': reverse('django_ledger:invoice-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'products_services',
                        'title': 'Products & Services',
                        'url': reverse('django_ledger:item-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Unit of Measures',
                        'url': reverse('django_ledger:uom-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                ]

            },
            {
                'type': 'links',
                'title': 'Reports',
                'links': [
                    {
                        'type': 'link',
                        'title': 'Balance Sheet',
                        'url': reverse('django_ledger:entity-bs', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Income Statement',
                        'url': reverse('django_ledger:entity-ic', kwargs={'entity_slug': ENTITY_SLUG})
                    }
                ]
            },
            {
                'type': 'links',
                'title': 'Accounting',
                'links': [
                    {
                        'type': 'link',
                        'title': 'Chart of Accounts',
                        'url': reverse('django_ledger:account-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Ledgers',
                        'url': reverse('django_ledger:ledger-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Data Import',
                        'url': reverse('django_ledger:data-import-jobs-list', kwargs={'entity_slug': ENTITY_SLUG})
                    }
                ]
            },
            {
                'type': 'links',
                'title': 'Administration',
                'links': [
                    {
                        'type': 'link',
                        'title': 'My Entities',
                        'url': reverse('django_ledger:home')
                    },
                    {
                        'type': 'link',
                        'title': 'Entity Settings',
                        'url': reverse('django_ledger:entity-update', kwargs={'entity_slug': ENTITY_SLUG})
                    }
                ]
            }
        ]
        ctx['links'] = nav_menu_links
        ctx['request'] = context['request']
    return ctx


@register.inclusion_tag('django_ledger/tags/item_table.html', takes_context=True)
def items_table(context, queryset):
    entity_slug = context['view'].kwargs['entity_slug']
    return {
        'entity_slug': entity_slug,
        'item_list': queryset
    }


@register.inclusion_tag('django_ledger/tags/items_formset.html', takes_context=True)
def item_formset_table(context, item_formset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'invoice_pk': context['view'].kwargs['invoice_pk'],
        'total_amount_due': context['total_amount_due'],
        'item_formset': item_formset,
    }


@register.inclusion_tag('django_ledger/tags/uom_table.html', takes_context=True)
def uom_table(context, uom_queryset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'uom_list': uom_queryset
    }
