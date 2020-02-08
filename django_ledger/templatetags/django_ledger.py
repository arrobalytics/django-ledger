from datetime import datetime
from random import randint

from django import template
from django.core.exceptions import ValidationError

from django_ledger.abstracts.journal_entry import validate_activity
from django_ledger.forms.app_filters import EntityFilterForm, EndDateFilterForm, ActivityFilterForm
from django_ledger.io.roles import ROLES_INCOME, ROLES_EXPENSES
from django_ledger.models.utils import get_date_filter_session_key, get_default_entity_session_key

register = template.Library()


@register.filter(name='cs_thousands')
def cs_thousands(value):
    return '{:,}'.format(value)


@register.inclusion_tag('django_ledger/tags/balance_sheet.html', takes_context=True)
def balance_sheet_table(context):
    entity_model = context['entity']
    activity = context['request'].GET.get('activity')
    activity = validate_activity(activity, raise_404=True)
    return entity_model.digest(activity=activity)


@register.inclusion_tag('django_ledger/tags/income_statement.html', takes_context=True)
def income_statement_table(context, entity_model=None):
    if not entity_model:
        entity_model = context.get('entity')
    if not entity_model:
        raise ValidationError('No entity model detected.')
    activity = context['request'].GET.get('activity')
    ic_data = entity_model.income_statement(signs=True, activity=activity)
    income = [acc for acc in ic_data if acc['role'] in ROLES_INCOME]
    expenses = [acc for acc in ic_data if acc['role'] in ROLES_EXPENSES]
    for ex in expenses:
        ex['balance'] = -ex['balance']
    total_income = sum([acc['balance'] for acc in income])
    total_expenses = sum([acc['balance'] for acc in expenses])
    total_income_loss = total_income - total_expenses

    return {
        'ic_data': ic_data,
        'income': income,
        'total_income': total_income,
        'expenses': expenses,
        'total_expenses': total_expenses,
        'total_income_loss': total_income_loss
    }


@register.inclusion_tag('django_ledger/tags/jes_table.html', takes_context=True)
def jes_table(context, je_queryset):
    return {
        'jes': je_queryset,
        'entity_slug': context['view'].kwargs['entity_slug']
    }


@register.inclusion_tag('django_ledger/tags/txs_table.html')
def txs_table(je_model):
    txs_queryset = je_model.txs.all()
    total_credits = sum([tx.amount for tx in txs_queryset if tx.tx_type == 'credit'])
    total_debits = sum([tx.amount for tx in txs_queryset if tx.tx_type == 'debit'])
    return {
        'txs': txs_queryset,
        'total_debits': total_debits,
        'total_credits': total_credits
    }


@register.inclusion_tag('django_ledger/tags/ledgers_table.html', takes_context=True)
def ledgers_table(context, ledgers_queryset):
    return {
        'ledgers': ledgers_queryset,
        'entity_slug': context['view'].kwargs['entity_slug']
    }


@register.inclusion_tag('django_ledger/tags/accounts_table.html')
def accounts_table(accounts_queryset):
    return {
        'accounts': accounts_queryset
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


# todo: rename template to entity_filter.
@register.inclusion_tag('django_ledger/tags/default_entity_form.html', takes_context=True)
def entity_filter(context):
    user = context['user']
    session_key = get_default_entity_session_key()
    default_entity_id = context['request'].session.get(session_key)
    default_entity_form = EntityFilterForm(user_model=user,
                                           default_entity=default_entity_id)
    return {
        'default_entity_form': default_entity_form
    }


# todo: rename template to date_form_filter.
@register.inclusion_tag('django_ledger/tags/date_form.html', takes_context=True)
def date_end_filter(context):
    entity_slug = context['view'].kwargs.get('entity_slug')
    session_item = get_date_filter_session_key(entity_slug)
    session = context['request'].session
    date_filter = session.get(session_item)
    identity = randint(0, 1000000)
    if entity_slug:
        form = EndDateFilterForm(form_id=identity, initial={
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
    session_item = get_date_filter_session_key(entity_slug)
    session = context['request'].session
    date_filter = session.get(session_item)
    if not date_filter:
        date_filter = datetime.now().date().strftime('%Y-%m-%d')
        session[session_item] = date_filter
    return date_filter
