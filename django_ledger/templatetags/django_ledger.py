from django import template
from django.urls import reverse

register = template.Library()


@register.inclusion_tag('django_ledger/tags/txs_table.html', takes_context=True)
def txs_table(context):
    kwargs = context['view'].kwargs
    txs_form_url = reverse('django_ledger:txs', kwargs={
        'entity_slug': kwargs['entity_slug'],
        'ledger_pk': kwargs['ledger_pk'],
        'je_pk': kwargs['je_pk'],
    })
    context['txs_form_url'] = txs_form_url
    return context


@register.inclusion_tag('django_ledger/tags/balance_sheet.html')
def balance_sheet(entity):
    bs_data = entity.balance_sheet()
    assets = [acc for acc in bs_data if acc['role_bs'] == 'assets']
    liabilities = [acc for acc in bs_data if acc['role_bs'] == 'liabilities']
    equity = [acc for acc in bs_data if acc['role_bs'] == 'equity']
    capital = [acc for acc in equity if acc['role'] in ['cap', 'capj']]
    earnings = [acc for acc in equity if acc['role'] in ['ex', 'in']]
    total_assets = sum(
        [acc['balance'] for acc in assets if acc['balance_type'] == 'debit'] +
        [-acc['balance'] for acc in assets if acc['balance_type'] == 'credit'])
    total_liabilities = sum(
        [acc['balance'] for acc in liabilities if acc['balance_type'] == 'credit'] +
        [-acc['balance'] for acc in liabilities if acc['balance_type'] == 'debit'])
    total_capital = sum(
        [acc['balance'] for acc in capital if acc['balance_type'] == 'credit'] +
        [-acc['balance'] for acc in capital if acc['balance_type'] == 'debit'])
    retained_earnings = sum(
        [acc['balance'] for acc in earnings if acc['balance_type'] == 'credit'] +
        [-acc['balance'] for acc in earnings if acc['balance_type'] == 'debit'])
    total_equity = total_capital + retained_earnings - total_liabilities
    total_liabilities_equity = total_liabilities + total_capital + retained_earnings
    return {
        'bs_data': bs_data,
        'assets': assets,
        'total_assets': total_assets,
        'liabilities': liabilities,
        'total_liabilities': total_liabilities,
        'equity': equity,
        'total_equity': total_equity,
        'capital': capital,
        'total_capital': total_capital,
        'earnings': earnings,
        'retained_earnings': retained_earnings,
        'total_liabilities_equity': total_liabilities_equity
    }


@register.inclusion_tag('django_ledger/tags/income_statememt.html')
def income_statement(entity):
    ic_data = entity.income_statement()
    income = [acc for acc in ic_data if acc['role'] in ['in']]
    expenses = [acc for acc in ic_data if acc['role'] in ['ex']]
    total_income = sum(
        [acc['balance'] for acc in income if acc['balance_type'] == 'credit'] +
        [-acc['balance'] for acc in income if acc['balance_type'] == 'debit'])
    total_expenses = -sum(
        [acc['balance'] for acc in expenses if acc['balance_type'] == 'credit'] +
        [-acc['balance'] for acc in expenses if acc['balance_type'] == 'debit'])

    return {
        'ic_data': ic_data,
        'income': income,
        'total_income': total_income,
        'expenses': expenses,
        'total_expenses': total_expenses,
        'total_income_loss': total_income - total_expenses
    }


@register.inclusion_tag('django_ledger/tags/transactions.html')
def je_txs(journal_entry):
    txs = journal_entry.txs.all()
    total_credits = sum([tx.amount for tx in txs if tx.tx_type == 'credit'])
    total_debits = sum([tx.amount for tx in txs if tx.tx_type == 'debit'])
    return {
        'txs': txs,
        'total_debits': total_debits,
        'total_credits': total_credits
    }
