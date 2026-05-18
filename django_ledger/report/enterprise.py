"""
Enterprise report data helpers.
"""
from __future__ import annotations

from django.db.models import Sum

from django_ledger.models.enterprise import (
    AuditEventModel,
    BankStatementLineModel,
    BudgetLineModel,
    DepreciationScheduleModel,
    FixedAssetModel,
    PaymentModel,
    TaxLineModel,
)
from django_ledger.models.transactions import TransactionModel


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
    qs = PaymentModel.objects.for_entity(entity_model).filter(direction=PaymentModel.PAYMENT_AR)
    if as_of_date:
        qs = qs.filter(payment_date__lte=as_of_date)
    return qs.values('customer_id', 'currency_id').annotate(
        total=Sum('amount'),
        unapplied=Sum('unapplied_amount'),
    )


def get_ap_aging_data(entity_model, as_of_date=None):
    qs = PaymentModel.objects.for_entity(entity_model).filter(direction=PaymentModel.PAYMENT_AP)
    if as_of_date:
        qs = qs.filter(payment_date__lte=as_of_date)
    return qs.values('vendor_id', 'currency_id').annotate(
        total=Sum('amount'),
        unapplied=Sum('unapplied_amount'),
    )


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
    return list(budget_lines)


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
