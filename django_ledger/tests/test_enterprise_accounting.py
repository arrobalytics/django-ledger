from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from django_ledger.models import (
    AccountingPeriodModel,
    BankAccountModel,
    BankStatementModel,
    CurrencyModel,
    PaymentModel,
    TaxAuthorityModel,
    TaxCodeModel,
    TaxRateModel,
)
from django_ledger.models.enterprise import AuditEventModel
from django_ledger.report.enterprise import get_audit_log_export_data, get_tax_summary_data
from django_ledger.services.enterprise import (
    allocate_payment,
    calculate_tax,
    close_period,
    create_audit_event,
    import_bank_statement_lines,
    reconcile_statement,
    reopen_period,
)
from django_ledger.tests.base import DjangoLedgerBaseTest


class EnterpriseAccountingTests(DjangoLedgerBaseTest):
    def test_audit_events_are_immutable(self):
        entity_model = self.get_random_entity_model()
        audit_event = create_audit_event(
            entity_model=entity_model,
            action=AuditEventModel.ACTION_CREATE,
            actor=self.user_model,
            after={'status': 'created'},
        )

        audit_event.after = {'status': 'changed'}
        with self.assertRaises(ValidationError):
            audit_event.save()
        with self.assertRaises(ValidationError):
            audit_event.delete()

        self.assertEqual(get_audit_log_export_data(entity_model).count(), 1)

    def test_close_and_reopen_accounting_period(self):
        entity_model = self.get_random_entity_model()
        period = AccountingPeriodModel.objects.create(
            entity_model=entity_model,
            fiscal_year=2026,
            period=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        close_period(accounting_period=period, user_model=self.user_model)
        period.refresh_from_db()
        self.assertEqual(period.status, AccountingPeriodModel.STATUS_CLOSED)
        self.assertIsNotNone(period.closed_at)

        reopen_period(accounting_period=period, user_model=self.user_model, reason='Correction required')
        period.refresh_from_db()
        self.assertEqual(period.status, AccountingPeriodModel.STATUS_REOPENED)
        self.assertEqual(period.reopen_reason, 'Correction required')

    def test_tax_calculation_and_summary(self):
        entity_model = self.get_random_entity_model()
        authority = TaxAuthorityModel.objects.create(entity_model=entity_model, name='Generic Tax Authority')
        tax_code = TaxCodeModel.objects.create(
            entity_model=entity_model,
            authority=authority,
            code='VAT10',
            name='VAT 10%',
            tax_type=TaxCodeModel.TAX_OUTPUT,
        )
        TaxRateModel.objects.create(
            entity_model=entity_model,
            tax_code=tax_code,
            rate=Decimal('0.100000'),
            effective_date=timezone.localdate(),
        )

        tax_line = calculate_tax(
            entity_model=entity_model,
            target=tax_code,
            tax_code=tax_code,
            taxable_amount=Decimal('100.00'),
        )

        self.assertEqual(tax_line.tax_amount, Decimal('10.00'))
        summary = list(get_tax_summary_data(entity_model))
        self.assertEqual(summary[0]['tax_amount'], Decimal('10.00'))

    def test_payment_allocation_updates_unapplied_amount(self):
        entity_model = self.get_random_entity_model()
        currency = CurrencyModel.objects.create(code='USD', name='US Dollar', symbol='$')
        payment = PaymentModel.objects.create(
            entity_model=entity_model,
            direction=PaymentModel.PAYMENT_AR,
            payment_date=timezone.localdate(),
            amount=Decimal('250.00'),
            unapplied_amount=Decimal('250.00'),
            currency=currency,
        )

        allocation = allocate_payment(
            payment=payment,
            target=payment,
            amount=Decimal('100.00'),
        )

        payment.refresh_from_db()
        self.assertEqual(allocation.amount, Decimal('100.00'))
        self.assertEqual(payment.unapplied_amount, Decimal('150.00'))

    def test_bank_statement_reconciliation_status(self):
        entity_model = self.get_random_entity_model()
        bank_account = BankAccountModel.objects.filter(entity_model=entity_model).first()
        statement = BankStatementModel.objects.create(
            entity_model=entity_model,
            bank_account=bank_account,
            statement_id='stmt-1',
            date_start=date(2026, 1, 1),
            date_end=date(2026, 1, 31),
        )
        import_bank_statement_lines(
            statement_model=statement,
            rows=[
                {
                    'posted_date': date(2026, 1, 15),
                    'amount': Decimal('42.00'),
                    'payee': 'Vendor',
                    'memo': 'Unmatched item',
                    'reference': 'abc',
                }
            ],
        )

        reconciliation = reconcile_statement(statement_model=statement, user_model=self.user_model)

        self.assertEqual(reconciliation.status, reconciliation.STATUS_REVIEW)
