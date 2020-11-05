from datetime import datetime, timedelta
from itertools import groupby
from random import randint

from django import template
from django.utils.timezone import now

from django_ledger import __version__
from django_ledger.forms.app_filters import EntityFilterForm, AsOfDateFilterForm, ActivityFilterForm
from django_ledger.models import TransactionModel, BillModel, InvoiceModel
from django_ledger.models.journalentry import validate_activity
from django_ledger.settings import DJANGO_LEDGER_FINANCIAL_ANALYSIS
from django_ledger.utils import get_date_filter_session_key, get_default_entity_session_key

register = template.Library()


@register.simple_tag(name='current_version')
def current_version():
    return __version__


@register.filter(name='cs_thousands')
def cs_thousands(value):
    if value:
        return '{0:,.2f}'.format(value)
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
def balance_sheet_table(context):
    ledger_or_entity = context['object']
    user_model = context['user']
    activity = context['request'].GET.get('activity')
    activity = validate_activity(activity, raise_404=True)
    end_date_session_key = get_date_filter_session_key(entity_slug=ledger_or_entity.uuid)
    end_date_filter = context['request'].session.get(end_date_session_key)
    # todo: incorporate digest in context???
    return ledger_or_entity.digest(activity=activity,
                                   user_model=user_model,
                                   equity_only=False,
                                   as_of=end_date_filter,
                                   process_groups=True)


@register.inclusion_tag('django_ledger/tags/income_statement.html', takes_context=True)
def income_statement_table(context):
    ledger_or_entity = context['object']
    user_model = context['user']
    activity = context['request'].GET.get('activity')
    activity = validate_activity(activity, raise_404=True)
    end_date_session_key = get_date_filter_session_key(entity_slug=ledger_or_entity.uuid)
    end_date_filter = context['request'].session.get(end_date_session_key)
    # todo: incorporate digest in context???
    return ledger_or_entity.digest(activity=activity,
                                   user_model=user_model,
                                   as_of=end_date_filter,
                                   equity_only=True,
                                   process_groups=True)


@register.inclusion_tag('django_ledger/tags/bank_accounts_table.html', takes_context=True)
def bank_account_table(context):
    return context


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
def session_entity_name(context):
    session_key = get_default_entity_session_key()
    session = context['request'].session
    return session.get(session_key)['entity_name']


# todo: rename template to date_form_filter.
@register.inclusion_tag('django_ledger/tags/date_filter.html', takes_context=True)
def date_filter(context, inline=False):
    entity_slug = context['view'].kwargs.get('entity_slug')
    session_item = get_date_filter_session_key(entity_slug)
    session = context['request'].session
    # todo: move this action to a function...
    date_filter = datetime.fromisoformat(session.get(session_item)) - timedelta(days=1)
    identity = randint(0, 1000000)
    if entity_slug:
        form = AsOfDateFilterForm(form_id=identity, initial={
            'entity_slug': context['view'].kwargs['entity_slug'],
            'date': date_filter
        })
        next_url = context['request'].path
        return {
            'date_form': form,
            'form_id': identity,
            'entity_slug': entity_slug,
            'date_filter': date_filter,
            'next': next_url,
            'inline': inline
        }


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


@register.simple_tag(takes_context=True)
def current_end_date_filter(context):
    entity_slug = context['view'].kwargs.get('entity_slug')
    session_key = get_date_filter_session_key(entity_slug)
    session = context['request'].session
    filter_iso = session.get(session_key)
    if not filter_iso:
        now_tz = now()
        new_filter = datetime(year=now_tz.year,
                              month=now_tz.month,
                              day=now_tz.day,
                              hour=0)
        new_filter += timedelta(days=1)
        session[session_key] = new_filter.isoformat()
        return now_tz.date()
    else:
        dt_filter = datetime.fromisoformat(filter_iso)
        return (dt_filter - timedelta(days=1)).date()


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
