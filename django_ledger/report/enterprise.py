"""
Enterprise report data helpers.
"""
from __future__ import annotations

from django.db.models import Sum
from django.utils import timezone

from django_ledger.models.enterprise import (
    AuditEventModel,
    BankStatementLineModel,
    BudgetLineModel,
    DepreciationScheduleModel,
    FixedAssetModel,
    PaymentModel,
    TaxLineModel,
)
from django_ledger.models.bill import BillModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.transactions import TransactionModel


def _aging_bucket(due_date, as_of_date):
    if not due_date:
        return 'current'
    days = (as_of_date - due_date).days
    if days <= 0:
        return 'current'
    if days <= 30:
        return '1_30'
    if days <= 60:
        return '31_60'
    if days <= 90:
        return '61_90'
    return 'over_90'


def _document_aging_rows(qs, party_field: str, as_of_date=None):
    as_of_date = as_of_date or timezone.localdate()
    rows = {}
    for obj in qs:
        open_amount = (obj.amount_due or 0) - (obj.amount_paid or 0)
        if open_amount <= 0:
            continue
        key = (getattr(obj, f'{party_field}_id'), getattr(obj, 'currency_id', None))
        row = rows.setdefault(key, {
            f'{party_field}_id': key[0],
            'currency_id': key[1],
            'current': 0,
            '1_30': 0,
            '31_60': 0,
            '61_90': 0,
            'over_90': 0,
            'total': 0,
        })
        bucket = _aging_bucket(obj.date_due, as_of_date)
        row[bucket] += open_amount
        row['total'] += open_amount
    return list(rows.values())


def get_trial_balance_data(entity_model, from_date=None, to_date=None):
    qs = TransactionModel.objects.for_entity(entity_model=entity_model).with_annotated_details()
    if from_date:
        qs = qs.filter(journal_entry__timestamp__date__gte=from_date)
    if to_date:
        qs = qs.filter(journal_entry__timestamp__date__lte=to_date)
    return qs.values(
        'account_id',
        'account_code',
        'account_name',
        'tx_type',
    ).annotate(
        balance=Sum('amount'),
    ).order_by('account_code', 'tx_type')


def get_general_ledger_data(entity_model, from_date=None, to_date=None, account_model=None):
    qs = TransactionModel.objects.for_entity(entity_model=entity_model).with_annotated_details()
    if account_model:
        qs = qs.filter(account=account_model)
    if from_date:
        qs = qs.filter(journal_entry__timestamp__date__gte=from_date)
    if to_date:
        qs = qs.filter(journal_entry__timestamp__date__lte=to_date)
    return qs.order_by('journal_entry__timestamp', 'account__code')


def get_ar_aging_data(entity_model, as_of_date=None):
    qs = InvoiceModel.objects.for_entity(entity_model=entity_model).select_related('customer')
    if as_of_date:
        qs = qs.filter(date_draft__lte=as_of_date)
    return _document_aging_rows(qs, 'customer', as_of_date)


def get_ap_aging_data(entity_model, as_of_date=None):
    qs = BillModel.objects.for_entity(entity_model=entity_model).select_related('vendor')
    if as_of_date:
        qs = qs.filter(date_draft__lte=as_of_date)
    return _document_aging_rows(qs, 'vendor', as_of_date)


def get_customer_statement_data(entity_model, customer_model, from_date=None, to_date=None):
    invoices = InvoiceModel.objects.for_entity(entity_model=entity_model).filter(customer=customer_model)
    payments = PaymentModel.objects.for_entity(entity_model).filter(direction=PaymentModel.PAYMENT_AR, customer=customer_model)
    if from_date:
        invoices = invoices.filter(date_draft__gte=from_date)
        payments = payments.filter(payment_date__gte=from_date)
    if to_date:
        invoices = invoices.filter(date_draft__lte=to_date)
        payments = payments.filter(payment_date__lte=to_date)
    return {
        'customer': customer_model,
        'invoices': invoices.order_by('date_draft'),
        'payments': payments.order_by('payment_date'),
    }


def get_vendor_statement_data(entity_model, vendor_model, from_date=None, to_date=None):
    bills = BillModel.objects.for_entity(entity_model=entity_model).filter(vendor=vendor_model)
    payments = PaymentModel.objects.for_entity(entity_model).filter(direction=PaymentModel.PAYMENT_AP, vendor=vendor_model)
    if from_date:
        bills = bills.filter(date_draft__gte=from_date)
        payments = payments.filter(payment_date__gte=from_date)
    if to_date:
        bills = bills.filter(date_draft__lte=to_date)
        payments = payments.filter(payment_date__lte=to_date)
    return {
        'vendor': vendor_model,
        'bills': bills.order_by('date_draft'),
        'payments': payments.order_by('payment_date'),
    }


def get_tax_summary_data(entity_model, from_date=None, to_date=None):
    qs = TaxLineModel.objects.for_entity(entity_model)
    if from_date:
        qs = qs.filter(created__date__gte=from_date)
    if to_date:
        qs = qs.filter(created__date__lte=to_date)
    return qs.values('tax_code_id', 'tax_code__code', 'tax_code__tax_type').annotate(
        taxable_amount=Sum('taxable_amount'),
        tax_amount=Sum('tax_amount'),
    ).order_by('tax_code__code')


def get_bank_reconciliation_data(statement_model):
    return {
        'statement': statement_model,
        'matched': BankStatementLineModel.objects.filter(statement_model=statement_model, matched_transaction__isnull=False),
        'unmatched': BankStatementLineModel.objects.filter(statement_model=statement_model, matched_transaction__isnull=True, ignored=False),
        'ignored': BankStatementLineModel.objects.filter(statement_model=statement_model, ignored=True),
    }


def get_budget_vs_actual_data(budget_version):
    budget_lines = BudgetLineModel.objects.filter(budget_version=budget_version).values(
        'account_model_id',
        'account_model__code',
        'account_model__name',
    ).annotate(
        budget_amount=Sum('amount'),
    )
    actuals = TransactionModel.objects.for_entity(entity_model=budget_version.entity_model).values(
        'account_id',
    ).annotate(
        actual_amount=Sum('amount'),
    )
    actual_map = {row['account_id']: row['actual_amount'] for row in actuals}
    rows = []
    for line in budget_lines:
        actual_amount = actual_map.get(line['account_model_id'], 0)
        line['actual_amount'] = actual_amount
        line['variance_amount'] = actual_amount - line['budget_amount']
        rows.append(line)
    return rows


def get_fixed_asset_register(entity_model):
    return FixedAssetModel.objects.for_entity(entity_model).select_related('category', 'depreciation_method')


def get_depreciation_summary(entity_model):
    return DepreciationScheduleModel.objects.for_entity(entity_model).values(
        'fixed_asset_id',
        'fixed_asset__name',
    ).annotate(
        depreciation_amount=Sum('depreciation_amount'),
    ).order_by('fixed_asset__name')


def get_audit_log_export_data(entity_model, from_date=None, to_date=None):
    qs = AuditEventModel.objects.for_entity(entity_model).select_related('actor', 'content_type')
    if from_date:
        qs = qs.filter(created__date__gte=from_date)
    if to_date:
        qs = qs.filter(created__date__lte=to_date)
    return qs.order_by('-created')
