"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from calendar import month_abbr
from itertools import groupby
from random import randint

from django import template
from django.db.models import Sum
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.timezone import localdate

from django_ledger import __version__
from django_ledger.forms.app_filters import EntityFilterForm, ActivityFilterForm
from django_ledger.forms.feedback import BugReportForm, RequestNewFeatureForm
from django_ledger.io import BS_BUCKETS_ORDER, ACCOUNT_LIST_ROLE_ORDER
from django_ledger.io.io_mixin import validate_activity
from django_ledger.models import TransactionModel, BillModel, InvoiceModel, EntityUnitModel
from django_ledger.settings import (
    DJANGO_LEDGER_FINANCIAL_ANALYSIS, DJANGO_LEDGER_CURRENCY_SYMBOL,
    DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL)
from django_ledger.utils import get_default_entity_session_key, get_end_date_from_session, prepare_context_by_unit

register = template.Library()


@register.simple_tag(name='current_version')
def current_version():
    return __version__


@register.simple_tag(name='currency_symbol')
def currency_symbol(spaced: bool = False):
    if spaced or DJANGO_LEDGER_SPACED_CURRENCY_SYMBOL:
        return f'{DJANGO_LEDGER_CURRENCY_SYMBOL} '
    return DJANGO_LEDGER_CURRENCY_SYMBOL


@register.filter(name='absolute')
def absolute(value):
    if value:
        if isinstance(value, str):
            value = float(value)
        return abs(value)


@register.filter(name='currency_format')
def currency_format(value):
    if value:
        return number_format(value, decimal_pos=2, use_l10n=True, force_grouping=True)
    return 0


@register.filter(name='percentage')
def percentage(value):
    if value is not None:
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


@register.inclusion_tag('django_ledger/components/icon.html')
def icon(icon_name, size):
    return {
        'icon': icon_name,
        'size': size
    }


@register.inclusion_tag('django_ledger/financial_statements/tags/balance_sheet_statement.html', takes_context=True)
def balance_sheet_statement(context, io_model, to_date=None):
    user_model = context['user']
    activity = context['request'].GET.get('activity')
    entity_slug = context['view'].kwargs.get('entity_slug')

    if not to_date:
        to_date = context['to_date']

    # todo: clean this up!...
    prepare_context_by_unit(context)

    txs_qs, digest = io_model.digest(
        activity=activity,
        user_model=user_model,
        equity_only=False,
        entity_slug=entity_slug,
        unit_slug=context['unit_slug'],
        by_unit=context['by_unit'],
        to_date=to_date,
        signs=True,
        process_groups=True,
        process_balance_sheet=True)

    # todo: this can be moved to the digest function...
    digest['by_unit'] = context['by_unit']
    digest['unit_model'] = context['unit_model']
    digest['unit_slug'] = context['unit_slug']
    digest['entity_slug'] = entity_slug

    return digest


@register.inclusion_tag('django_ledger/financial_statements/tags/cash_flow_statement.html', takes_context=True)
def cash_flow_statement(context, io_model):
    user_model = context['user']
    entity_slug = context['view'].kwargs.get('entity_slug')
    from_date = context['from_date']
    to_date = context['to_date']

    prepare_context_by_unit(context)

    txs_qs, io_digest = io_model.digest(
        cash_flow_statement=True,
        by_activity=True,
        user_model=user_model,
        equity_only=False,
        signs=True,
        entity_slug=entity_slug,
        unit_slug=context['unit_slug'],
        by_unit=context['by_unit'],
        from_date=from_date,
        to_date=to_date,
        process_groups=True)

    io_digest['by_unit'] = context['by_unit']
    io_digest['unit_model'] = context['unit_model']
    io_digest['unit_slug'] = context['unit_slug']
    return io_digest


@register.inclusion_tag('django_ledger/financial_statements/tags/income_statement.html', takes_context=True)
def income_statement_table(context, io_model, from_date=None, to_date=None):
    user_model: EntityUnitModel = context['user']
    activity = context['request'].GET.get('activity')
    activity = validate_activity(activity, raise_404=True)
    entity_slug = context['view'].kwargs.get('entity_slug')

    if not from_date:
        from_date = context['from_date']
    if not to_date:
        to_date = context['to_date']

    prepare_context_by_unit(context)

    txs_qs, digest = io_model.digest(
        activity=activity,
        user_model=user_model,
        entity_slug=entity_slug,
        unit_slug=context['unit_slug'],
        by_unit=context['by_unit'],
        from_date=from_date,
        to_date=to_date,
        equity_only=True,
        process_groups=True)

    digest['by_unit'] = context['by_unit']
    digest['unit_model'] = context['unit_model']
    digest['unit_slug'] = context['unit_slug']
    return digest


@register.inclusion_tag('django_ledger/bank_account/tags/bank_accounts_table.html', takes_context=True)
def bank_account_table(context, bank_account_qs):
    entity_slug = context['view'].kwargs['entity_slug']
    return {
        'bank_account_qs': bank_account_qs,
        'entity_slug': entity_slug
    }


@register.inclusion_tag('django_ledger/data_import/tags/data_import_job_list_table.html', takes_context=True)
def data_import_job_list_table(context):
    return context


@register.inclusion_tag('django_ledger/data_import/tags/data_import_job_txs_table.html', takes_context=True)
def data_import_job_txs_pending(context):
    return context


@register.inclusion_tag('django_ledger/data_import/tags/data_import_job_txs_imported.html', takes_context=True)
def data_import_job_txs_imported(context):
    return context


@register.inclusion_tag('django_ledger/journal_entry/tags/je_table.html', takes_context=True)
def jes_table(context, next_url=None):
    entity_slug = context['view'].kwargs['entity_slug']
    ledger_pk = context['view'].kwargs['ledger_pk']
    if not next_url:
        next_url = reverse('django_ledger:je-list',
                           kwargs={
                               'entity_slug': entity_slug,
                               'ledger_pk': ledger_pk
                           })
    return {
        'jes': context['journal_entries'],
        'entity_slug': context['view'].kwargs['entity_slug'],
        'ledger_pk': context['view'].kwargs['ledger_pk'],
        'next_url': next_url
    }


@register.inclusion_tag('django_ledger/journal_entry/tags/je_txs_table.html')
def journal_entry_txs_table(journal_entry_model, style='detail'):
    txs_queryset = journal_entry_model.transactionmodel_set.all().select_related('account').order_by('account__code')
    total_credits = sum(tx.amount for tx in txs_queryset if tx.tx_type == 'credit')
    total_debits = sum(tx.amount for tx in txs_queryset if tx.tx_type == 'debit')
    return {
        'txs': txs_queryset,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'style': style
    }


@register.inclusion_tag('django_ledger/journal_entry/tags/je_txs_table.html', takes_context=True)
def bill_txs_table(context, bill_model: BillModel):
    txs_queryset = TransactionModel.objects.for_bill(
        bill_model=bill_model.uuid,
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


@register.inclusion_tag('django_ledger/journal_entry/tags/je_txs_table.html', takes_context=True)
def invoice_txs_table(context, invoice_model: InvoiceModel):
    txs_queryset = TransactionModel.objects.for_invoice(
        invoice_model=invoice_model,
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


@register.inclusion_tag('django_ledger/ledger/tags/ledgers_table.html', takes_context=True)
def ledgers_table(context):
    return {
        'ledgers': context['ledgers'],
        'entity_slug': context['view'].kwargs['entity_slug'],
    }


@register.inclusion_tag('django_ledger/invoice/tags/invoice_table.html', takes_context=True)
def invoice_table(context, invoice_qs):
    return {
        'invoices': invoice_qs,
        'entity_slug': context['view'].kwargs['entity_slug']
    }


@register.inclusion_tag('django_ledger/bills/includes/bill_table.html', takes_context=True)
def bill_table(context, bill_qs):
    return {
        'bills': bill_qs,
        'entity_slug': context['view'].kwargs['entity_slug']
    }


@register.inclusion_tag('django_ledger/purchase_order/includes/po_table.html', takes_context=True)
def po_table(context, purchase_order_qs):
    return {
        'po_list': purchase_order_qs,
        'entity_slug': context['view'].kwargs['entity_slug']
    }


@register.inclusion_tag('django_ledger/account/tags/accounts_table.html', takes_context=True)
def accounts_table(context, accounts_qs, title=None):
    return {
        'title': title,
        'entity_slug': context['view'].kwargs['entity_slug'],
        'accounts_gb': accounts_qs.gb_bs_role(),
    }


@register.inclusion_tag('django_ledger/customer/tags/customer_table.html', takes_context=True)
def customer_table(context):
    return context


@register.inclusion_tag('django_ledger/vendor/tags/vendor_table.html', takes_context=True)
def vendor_table(context):
    return context


@register.inclusion_tag('django_ledger/account/tags/account_txs_table.html', takes_context=True)
def account_txs_table(context, txs_qs):
    return {
        'transactions': txs_qs,
        'total_credits': sum(tx.amount for tx in txs_qs if tx.tx_type == 'credit'),
        'total_debits': sum(tx.amount for tx in txs_qs if tx.tx_type == 'debit'),
        'entity_slug': context['view'].kwargs['entity_slug'],
        'account_pk': context['view'].kwargs['account_pk']
    }


@register.inclusion_tag('django_ledger/components/breadcrumbs.html', takes_context=True)
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


@register.inclusion_tag('django_ledger/components/default_entity.html', takes_context=True)
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
    try:
        entity_name = session.get(session_key)['entity_name']
    except KeyError:
        entity_name = 'Django Ledger'
    except TypeError:
        entity_name = 'Django Ledger'
    return entity_name


# todo: rename template to activity_form_filter.
@register.inclusion_tag('django_ledger/components/activity_form.html', takes_context=True)
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


@register.inclusion_tag('django_ledger/components/date_picker.html', takes_context=True)
def date_picker(context, nav_url=None, date_picker_id=None):
    try:
        entity_slug = context['view'].kwargs.get('entity_slug')
    except KeyError:
        entity_slug = context['entity_slug']

    if not date_picker_id:
        date_picker_id = f'djl-datepicker-{randint(10000, 99999)}'

    if 'date_picker_ids' not in context:
        context['date_picker_ids'] = list()
    context['date_picker_ids'].append(date_picker_id)

    date_navigation_url = nav_url if nav_url else context.get('date_navigation_url')
    return {
        'entity_slug': entity_slug,
        'date_picker_id': date_picker_id,
        'date_navigation_url': date_navigation_url
    }


@register.simple_tag(takes_context=True)
def get_current_end_date_filter(context):
    entity_slug = context['view'].kwargs.get('entity_slug')
    return get_end_date_from_session(entity_slug, context['request'])


@register.inclusion_tag('django_ledger/components/chart_container.html')
def chart_container(chart_id, endpoint=None):
    return {
        'chart_id': chart_id,
        'endpoint': endpoint
    }


@register.inclusion_tag('django_ledger/components/modals.html', takes_context=True)
def modal_action(context, model, http_method: str = 'post', entity_slug: str = None):
    if not entity_slug:
        entity_slug = context['view'].kwargs['entity_slug']
    action_url = model.get_mark_as_paid_url(entity_slug=entity_slug)
    return {
        'object': model,
        'action_url': action_url,
        'http_method': http_method,
        'message': f'Do you want to mark {model.__class__._meta.verbose_name} {model.get_document_id()} as paid?'
    }


@register.inclusion_tag('django_ledger/components/modals_v2.html', takes_context=True)
def modal_action_v2(context, model, action_url: str, message: str, html_id: str, http_method: str = 'get'):
    return {
        'object': model,
        'action_url': action_url,
        'http_method': http_method,
        'message': message,
        'html_id': html_id
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


@register.inclusion_tag('django_ledger/components/feedback_button.html', takes_context=True)
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


@register.inclusion_tag('django_ledger/components/period_navigator.html', takes_context=True)
def period_navigation(context, base_url: str):
    kwargs = dict()
    entity_slug = context['view'].kwargs['entity_slug']
    kwargs['entity_slug'] = entity_slug

    if context['view'].kwargs.get('ledger_pk'):
        kwargs['ledger_pk'] = context['view'].kwargs.get('ledger_pk')

    if context['view'].kwargs.get('account_pk'):
        kwargs['account_pk'] = context['view'].kwargs.get('account_pk')

    if context['view'].kwargs.get('unit_slug'):
        kwargs['unit_slug'] = context['view'].kwargs.get('unit_slug')

    ctx = dict()
    ctx['year'] = context['year']
    ctx['has_year'] = context.get('has_year')
    ctx['has_quarter'] = context.get('has_quarter')
    ctx['has_month'] = context.get('has_month')
    ctx['has_date'] = context.get('has_date')
    ctx['previous_year'] = context['previous_year']

    kwargs['year'] = context['previous_year']
    ctx['previous_year_url'] = reverse(f'django_ledger:{base_url}-year', kwargs=kwargs)
    ctx['next_year'] = context['next_year']

    kwargs['year'] = context['next_year']
    ctx['next_year_url'] = reverse(f'django_ledger:{base_url}-year', kwargs=kwargs)

    kwargs['year'] = context['year']
    ctx['current_year_url'] = reverse(f'django_ledger:{base_url}-year', kwargs=kwargs)

    dt = localdate()
    KWARGS_CURRENT_MONTH = {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'year': dt.year,
        'month': dt.month
    }
    if 'unit_slug' in kwargs:
        KWARGS_CURRENT_MONTH['unit_slug'] = kwargs['unit_slug']
    if 'account_pk' in kwargs:
        KWARGS_CURRENT_MONTH['account_pk'] = kwargs['account_pk']
    if 'ledger_pk' in kwargs:
        KWARGS_CURRENT_MONTH['ledger_pk'] = kwargs['ledger_pk']

    ctx['current_month_url'] = reverse(f'django_ledger:{base_url}-month',
                                       kwargs=KWARGS_CURRENT_MONTH)

    quarter_urls = list()
    ctx['quarter'] = context.get('quarter')
    for Q in range(1, 5):
        kwargs['quarter'] = Q
        quarter_urls.append({
            'url': reverse(f'django_ledger:{base_url}-quarter', kwargs=kwargs),
            'quarter': Q,
            'quarter_name': f'Q{Q}'
        })
    del kwargs['quarter']
    ctx['quarter_urls'] = quarter_urls

    month_urls = list()
    ctx['month'] = context.get('month')
    for M in range(1, 13):
        kwargs['month'] = M
        month_urls.append({
            'url': reverse(f'django_ledger:{base_url}-month', kwargs=kwargs),
            'month': M,
            'month_abbr': month_abbr[M]
        })
    ctx['month_urls'] = month_urls
    ctx['from_date'] = context['from_date']
    ctx['to_date'] = context['to_date']
    ctx.update(kwargs)

    ctx['date_navigation_url'] = context.get('date_navigation_url')

    return ctx


@register.inclusion_tag('django_ledger/components/menu.html', takes_context=True)
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
                'url': reverse('django_ledger:entity-dashboard', kwargs={'entity_slug': ENTITY_SLUG})
            },
            {
                'type': 'links',
                'title': 'Management',
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
                        'title': 'Estimates & Contracts',
                        'url': reverse('django_ledger:customer-estimate-list', kwargs={'entity_slug': ENTITY_SLUG})
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
                        'type': 'link',
                        'title': 'Purchase Orders',
                        'url': reverse('django_ledger:po-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Inventory',
                        'url': reverse('django_ledger:inventory-list', kwargs={'entity_slug': ENTITY_SLUG})
                    }

                ]
            },
            {
                'type': 'links',
                'title': 'Your Lists',
                'links': [
                    {
                        'type': 'link',
                        'title': 'Entity Units',
                        'url': reverse('django_ledger:unit-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Products',
                        'url': reverse('django_ledger:product-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Services',
                        'url': reverse('django_ledger:service-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Business Expenses',
                        'url': reverse('django_ledger:expense-list', kwargs={'entity_slug': ENTITY_SLUG})
                    },
                    {
                        'type': 'link',
                        'title': 'Inventory Items',
                        'url': reverse('django_ledger:inventory-item-list', kwargs={'entity_slug': ENTITY_SLUG})
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
                    },
                    {
                        'type': 'link',
                        'title': 'Cash Flow Statement',
                        'url': reverse('django_ledger:entity-cf', kwargs={'entity_slug': ENTITY_SLUG})
                    },
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


@register.inclusion_tag('django_ledger/product/tags/product_table.html', takes_context=True)
def product_table(context, queryset):
    entity_slug = context['view'].kwargs['entity_slug']
    return {
        'entity_slug': entity_slug,
        'product_list': queryset
    }


@register.inclusion_tag('django_ledger/service/tags/services_table.html', takes_context=True)
def service_table(context, queryset):
    entity_slug = context['view'].kwargs['entity_slug']
    return {
        'entity_slug': entity_slug,
        'service_list': queryset
    }


@register.inclusion_tag('django_ledger/expense/tags/expense_item_table.html', takes_context=True)
def expense_item_table(context, queryset):
    entity_slug = context['view'].kwargs['entity_slug']
    return {
        'entity_slug': entity_slug,
        'expense_list': queryset
    }


@register.inclusion_tag('django_ledger/inventory/tags/inventory_item_table.html', takes_context=True)
def inventory_item_table(context, queryset):
    entity_slug = context['view'].kwargs['entity_slug']
    return {
        'entity_slug': entity_slug,
        'inventory_item_list': queryset
    }


@register.inclusion_tag('django_ledger/invoice/tags/invoice_item_formset.html', takes_context=True)
def invoice_item_formset_table(context, itemtxs_formset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'invoice_model': context['invoice'],
        'total_amount__sum': context['total_amount__sum'],
        'itemtxs_formset': itemtxs_formset,
    }


@register.inclusion_tag('django_ledger/bills/tags/bill_item_formset.html', takes_context=True)
def bill_item_formset_table(context, item_formset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'bill_pk': context['view'].kwargs['bill_pk'],
        'total_amount__sum': context['total_amount__sum'],
        'item_formset': item_formset,
    }


@register.inclusion_tag('django_ledger/purchase_order/includes/po_item_formset.html', takes_context=True)
def po_item_formset_table(context, po_model, itemtxs_formset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'po_model': po_model,
        'itemtxs_formset': itemtxs_formset,
    }


@register.inclusion_tag('django_ledger/uom/tags/uom_table.html', takes_context=True)
def uom_table(context, uom_queryset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'uom_list': uom_queryset
    }


@register.inclusion_tag('django_ledger/inventory/tags/inventory_table.html', takes_context=True)
def inventory_table(context, queryset):
    ctx = {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'inventory_list': queryset
    }
    ctx.update(queryset.aggregate(inventory_total_value=Sum('total_value')))
    return ctx


@register.inclusion_tag('django_ledger/estimate/includes/estimate_table.html', takes_context=True)
def customer_estimate_table(context, queryset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'ce_list': queryset
    }


@register.inclusion_tag('django_ledger/estimate/includes/estimate_item_table.html', takes_context=True)
def estimate_item_table(context, queryset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'ce_model': context['estimate_model'],
        'ce_item_list': queryset
    }


@register.inclusion_tag('django_ledger/purchase_order/tags/po_item_table.html', takes_context=True)
def po_item_table(context, queryset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'po_model': context['po_model'],
        'po_item_list': queryset
    }


@register.inclusion_tag('django_ledger/estimate/tags/ce_item_formset.html', takes_context=True)
def customer_estimate_item_formset(context, item_formset):
    return {
        'entity_slug': context['view'].kwargs['entity_slug'],
        'ce_pk': context['view'].kwargs['ce_pk'],
        'ce_revenue_estimate__sum': context['ce_revenue_estimate__sum'],
        'ce_cost_estimate__sum': context['ce_cost_estimate__sum'],
        'item_formset': item_formset,
    }
