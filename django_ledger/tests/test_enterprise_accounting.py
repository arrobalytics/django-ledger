from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from django_ledger.models import (
    AccountingPeriodModel,
    ApprovalRequestModel,
    ApprovalPolicyModel,
    AssetCategoryModel,
    BankAccountModel,
    BankStatementModel,
    BudgetLineModel,
    BudgetModel,
    BudgetVersionModel,
    BillModel,
    CurrencyModel,
    DepreciationMethodModel,
    DimensionModel,
    DimensionValueModel,
    EntityRoleModel,
    EntityUnitModel,
    EnterpriseModelValidationError,
    FixedAssetModel,
    InvoiceModel,
    PaymentModel,
    TaxAuthorityModel,
    TaxCodeModel,
    TaxRateModel,
)
from django_ledger.models.enterprise import AuditEventModel
from django_ledger.report.enterprise import get_audit_log_export_data, get_budget_vs_actual_data, get_tax_summary_data
from django_ledger.services.enterprise import (
    approve_document,
    approve_budget_version,
    apply_document_currency,
    allocate_payment,
    assign_dimension,
    auto_match_bank_statement,
    assert_period_open,
    calculate_tax,
    close_period,
    create_payment,
    create_straight_line_depreciation_schedule,
    create_audit_event,
    get_realized_fx_gain_loss,
    import_bank_statement_csv,
    import_bank_statement_lines,
    match_bank_statement_line,
    post_payment,
    reconcile_statement,
    reverse_payment,
    reopen_period,
    request_approval,
)
from django_ledger.tests.base import DjangoLedgerBaseTest


class EnterpriseAccountingTests(DjangoLedgerBaseTest):
    def _create_test_unit(self, entity_model, name='Approval Unit'):
        unit_model = EntityUnitModel.add_root(
            entity=entity_model,
            name=name,
            slug='',
            document_prefix='APR',
        )
        unit_model.clean()
        unit_model.save()
        return unit_model

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

    def test_closed_accounting_period_blocks_period_operations(self):
        entity_model = self.get_random_entity_model()
        period = AccountingPeriodModel.objects.create(
            entity_model=entity_model,
            fiscal_year=2026,
            period=2,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            status=AccountingPeriodModel.STATUS_CLOSED,
        )

        with self.assertRaises(EnterpriseModelValidationError):
            assert_period_open(entity_model, period.start_date)

    def test_close_period_requires_finance_admin_or_owner_role(self):
        user_model_cls = get_user_model()
        entity_model = self.get_random_entity_model()
        period = AccountingPeriodModel.objects.create(
            entity_model=entity_model,
            fiscal_year=2026,
            period=3,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )
        finance_user = user_model_cls.objects.create_user(
            username='finance-close-user',
            password='NeverUseThisPassword12345',
            email='finance-close-user@djangoledger.com',
        )

        with self.assertRaises(EnterpriseModelValidationError):
            close_period(accounting_period=period, user_model=finance_user)

        EntityRoleModel.objects.create(
            entity_model=entity_model,
            user=finance_user,
            role=EntityRoleModel.ROLE_FINANCE_ADMIN,
        )

        close_period(accounting_period=period, user_model=finance_user)
        period.refresh_from_db()
        self.assertEqual(period.status, AccountingPeriodModel.STATUS_CLOSED)

    def test_reopen_period_requires_finance_admin_or_owner_role(self):
        user_model_cls = get_user_model()
        entity_model = self.get_random_entity_model()
        period = AccountingPeriodModel.objects.create(
            entity_model=entity_model,
            fiscal_year=2026,
            period=4,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            status=AccountingPeriodModel.STATUS_CLOSED,
        )
        finance_user = user_model_cls.objects.create_user(
            username='finance-reopen-user',
            password='NeverUseThisPassword12345',
            email='finance-reopen-user@djangoledger.com',
        )

        with self.assertRaises(EnterpriseModelValidationError):
            reopen_period(accounting_period=period, user_model=finance_user, reason='Need correction')

        EntityRoleModel.objects.create(
            entity_model=entity_model,
            user=finance_user,
            role=EntityRoleModel.ROLE_FINANCE_ADMIN,
        )

        reopen_period(accounting_period=period, user_model=finance_user, reason='Need correction')
        period.refresh_from_db()
        self.assertEqual(period.status, AccountingPeriodModel.STATUS_REOPENED)

    def test_request_approval_selects_matching_amount_policy(self):
        entity_model = self.get_random_entity_model()
        target = entity_model
        low_policy = ApprovalPolicyModel.objects.create(
            entity_model=entity_model,
            name='Low value approvals',
            document_type=ApprovalPolicyModel.DOCUMENT_ALL,
            min_amount=Decimal('0.00'),
            max_amount=Decimal('99.99'),
        )
        high_policy = ApprovalPolicyModel.objects.create(
            entity_model=entity_model,
            name='High value approvals',
            document_type=ApprovalPolicyModel.DOCUMENT_ALL,
            min_amount=Decimal('100.00'),
        )

        approval_request = request_approval(
            entity_model=entity_model,
            target=target,
            requested_by=self.user_model,
            amount=Decimal('250.00'),
        )

        self.assertEqual(approval_request.policy, high_policy)
        self.assertNotEqual(approval_request.policy, low_policy)

    def test_request_approval_prefers_vendor_specific_policy(self):
        entity_model = self.get_random_entity_model()
        bill_model = BillModel.objects.for_entity(entity_model=entity_model).select_related('vendor').first()

        generic_policy = ApprovalPolicyModel.objects.create(
            entity_model=entity_model,
            name='Generic bill approval',
            document_type='billmodel',
            min_amount=Decimal('0.00'),
        )
        vendor_policy = ApprovalPolicyModel.objects.create(
            entity_model=entity_model,
            name='Vendor-specific bill approval',
            document_type='billmodel',
            min_amount=Decimal('0.00'),
            vendor=bill_model.vendor,
        )

        approval_request = request_approval(
            entity_model=entity_model,
            target=bill_model,
            requested_by=self.user_model,
            amount=Decimal('50.00'),
        )

        self.assertEqual(approval_request.policy, vendor_policy)
        self.assertNotEqual(approval_request.policy, generic_policy)

    def test_request_approval_prefers_customer_specific_policy(self):
        entity_model = self.get_random_entity_model()
        invoice_model = InvoiceModel.objects.for_entity(entity_model=entity_model).select_related('customer').first()

        generic_policy = ApprovalPolicyModel.objects.create(
            entity_model=entity_model,
            name='Generic invoice approval',
            document_type='invoicemodel',
            min_amount=Decimal('0.00'),
        )
        customer_policy = ApprovalPolicyModel.objects.create(
            entity_model=entity_model,
            name='Customer-specific invoice approval',
            document_type='invoicemodel',
            min_amount=Decimal('0.00'),
            customer=invoice_model.customer,
        )

        approval_request = request_approval(
            entity_model=entity_model,
            target=invoice_model,
            requested_by=self.user_model,
            amount=Decimal('50.00'),
        )

        self.assertEqual(approval_request.policy, customer_policy)
        self.assertNotEqual(approval_request.policy, generic_policy)

    def test_request_approval_matches_entity_unit_and_account_role(self):
        entity_model = self.get_random_entity_model()
        account_model = self.get_random_account(entity_model=entity_model)
        unit_model = self._create_test_unit(entity_model, name='Approval Routing Unit')
        journal_entry_model = self.get_random_je(entity_model=entity_model)
        journal_entry_model.entity_unit = unit_model
        journal_entry_model.save(update_fields=['entity_unit', 'updated'])

        ApprovalPolicyModel.objects.create(
            entity_model=entity_model,
            name='Generic journal approval',
            document_type='journalentrymodel',
            min_amount=Decimal('0.00'),
        )
        specific_policy = ApprovalPolicyModel.objects.create(
            entity_model=entity_model,
            name='Specific journal approval',
            document_type='journalentrymodel',
            min_amount=Decimal('0.00'),
            entity_unit=unit_model,
        )
        account_policy = ApprovalPolicyModel.objects.create(
            entity_model=entity_model,
            name='Specific bill account approval',
            document_type='billmodel',
            min_amount=Decimal('0.00'),
            account_role=account_model.role,
        )
        bill_model = BillModel.objects.for_entity(entity_model=entity_model).first()
        bill_model.cash_account = account_model
        bill_model.save(update_fields=['cash_account', 'updated'])

        approval_request = request_approval(
            entity_model=entity_model,
            target=journal_entry_model,
            requested_by=self.user_model,
            amount=Decimal('75.00'),
        )
        bill_approval_request = request_approval(
            entity_model=entity_model,
            target=bill_model,
            requested_by=self.user_model,
            amount=Decimal('75.00'),
        )

        self.assertEqual(approval_request.policy, specific_policy)
        self.assertEqual(bill_approval_request.policy, account_policy)

    def test_approve_document_requires_approver_role(self):
        user_model_cls = get_user_model()
        entity_model = self.get_random_entity_model()
        approver_user = user_model_cls.objects.create_user(
            username='approval-user',
            password='NeverUseThisPassword12345',
            email='approval-user@djangoledger.com',
        )
        approval_request = ApprovalRequestModel.objects.create(
            entity_model=entity_model,
            requested_by=self.user_model,
            amount=Decimal('10.00'),
        )

        with self.assertRaises(EnterpriseModelValidationError):
            approve_document(approval_request=approval_request, user_model=approver_user)

        EntityRoleModel.objects.create(
            entity_model=entity_model,
            user=approver_user,
            role=EntityRoleModel.ROLE_APPROVER,
        )

        approve_document(approval_request=approval_request, user_model=approver_user)
        approval_request.refresh_from_db()
        self.assertEqual(approval_request.status, ApprovalRequestModel.STATUS_APPROVED)

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

    def test_tax_calculation_uses_rate_active_on_requested_date(self):
        entity_model = self.get_random_entity_model()
        authority = TaxAuthorityModel.objects.create(entity_model=entity_model, name='Generic Tax Authority')
        tax_code = TaxCodeModel.objects.create(
            entity_model=entity_model,
            authority=authority,
            code='VATD',
            name='VAT Dated',
            tax_type=TaxCodeModel.TAX_OUTPUT,
        )
        TaxRateModel.objects.create(
            entity_model=entity_model,
            tax_code=tax_code,
            rate=Decimal('0.050000'),
            effective_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
        TaxRateModel.objects.create(
            entity_model=entity_model,
            tax_code=tax_code,
            rate=Decimal('0.100000'),
            effective_date=date(2026, 2, 1),
        )

        tax_line = calculate_tax(
            entity_model=entity_model,
            target=tax_code,
            tax_code=tax_code,
            taxable_amount=Decimal('100.00'),
            on_date=date(2026, 1, 15),
        )

        self.assertEqual(tax_line.tax_amount, Decimal('5.00'))

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

    def test_payment_lifecycle_audits_and_reverses_allocations(self):
        entity_model = self.get_random_entity_model()
        currency = CurrencyModel.objects.create(code='CAD', name='Canadian Dollar', symbol='$')
        payment = create_payment(
            entity_model=entity_model,
            direction=PaymentModel.PAYMENT_AR,
            payment_date=timezone.localdate(),
            amount=Decimal('150.00'),
            user_model=self.user_model,
            currency=currency,
        )
        allocate_payment(payment=payment, target=payment, amount=Decimal('50.00'))

        post_payment(payment=payment, user_model=self.user_model)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentModel.STATUS_POSTED)

        reverse_payment(payment=payment, user_model=self.user_model, reason='Incorrect payment')
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentModel.STATUS_VOID)
        self.assertEqual(payment.unapplied_amount, Decimal('150.00'))
        self.assertFalse(payment.paymentallocationmodel_set.exists())
        self.assertGreaterEqual(get_audit_log_export_data(entity_model).count(), 3)

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

    def test_manual_bank_statement_match_marks_transaction_reconciled(self):
        entity_model = self.get_random_entity_model()
        transaction_model = self.get_random_transaction(entity_model=entity_model)
        bank_account = BankAccountModel.objects.filter(entity_model=entity_model).first()
        statement = BankStatementModel.objects.create(
            entity_model=entity_model,
            bank_account=bank_account,
            statement_id='stmt-2',
            date_start=date(2026, 1, 1),
            date_end=date(2026, 1, 31),
        )
        statement_line = import_bank_statement_lines(
            statement_model=statement,
            rows=[{
                'posted_date': date(2026, 1, 15),
                'amount': transaction_model.amount,
                'payee': 'Matched payee',
                'memo': 'Manual match',
                'reference': 'matched',
            }],
        )[0]

        match_bank_statement_line(
            statement_line=statement_line,
            transaction_model=transaction_model,
            user_model=self.user_model,
        )

        statement_line.refresh_from_db()
        transaction_model.refresh_from_db()
        self.assertEqual(statement_line.matched_transaction, transaction_model)
        self.assertTrue(transaction_model.reconciled)

    def test_bank_statement_csv_import_and_auto_match(self):
        entity_model = self.get_random_entity_model()
        transaction_model = self.get_random_transaction(entity_model=entity_model)
        bank_account = BankAccountModel.objects.filter(entity_model=entity_model).first()
        statement = BankStatementModel.objects.create(
            entity_model=entity_model,
            bank_account=bank_account,
            statement_id='stmt-csv',
            date_start=date(2026, 1, 1),
            date_end=date(2026, 1, 31),
        )
        posted_date = transaction_model.journal_entry.timestamp.date().isoformat()
        csv_text = f'posted_date,amount,payee,memo,reference\n{posted_date},{transaction_model.amount},Payee,Memo,{transaction_model.pk}\n'

        import_bank_statement_csv(statement_model=statement, csv_text=csv_text)
        matched = auto_match_bank_statement(statement_model=statement, user_model=self.user_model)

        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].matched_transaction, transaction_model)

    def test_currency_base_amount_and_realized_fx_calculation(self):
        entity_model = self.get_random_entity_model()
        usd = CurrencyModel.objects.create(code='USD', name='US Dollar', symbol='$')
        eur = CurrencyModel.objects.create(code='EUR', name='Euro', symbol='EUR')
        entity_model.base_currency = usd
        entity_model.save(update_fields=['base_currency', 'updated'])
        bill_model = BillModel.objects.for_entity(entity_model=entity_model).first()
        bill_model.amount_due = Decimal('100.00')

        apply_document_currency(target=bill_model, currency=eur, exchange_rate=Decimal('1.2000000000'))

        self.assertEqual(bill_model.base_amount_due, Decimal('120.00'))
        self.assertEqual(
            get_realized_fx_gain_loss(
                settlement_amount=Decimal('100.00'),
                settlement_rate=Decimal('1.3000000000'),
                document_amount=Decimal('100.00'),
                document_rate=Decimal('1.2000000000'),
            ),
            Decimal('10.00'),
        )

    def test_dimension_assignment_and_budget_approval(self):
        entity_model = self.get_random_entity_model()
        account_model = self.get_random_account(entity_model=entity_model)
        dimension = DimensionModel.objects.create(
            entity_model=entity_model,
            name='Operations',
            dimension_type=DimensionModel.DIMENSION_DEPARTMENT,
        )
        dimension_value = DimensionValueModel.objects.create(
            entity_model=entity_model,
            dimension=dimension,
            code='OPS',
            name='Operations',
        )
        assignment = assign_dimension(entity_model=entity_model, target=account_model, dimension_value=dimension_value)
        budget = BudgetModel.objects.create(entity_model=entity_model, name='FY26', fiscal_year=2026)
        budget_version = BudgetVersionModel.objects.create(entity_model=entity_model, budget=budget)
        BudgetLineModel.objects.create(
            entity_model=entity_model,
            budget_version=budget_version,
            account_model=account_model,
            amount=Decimal('100.00'),
        )

        approve_budget_version(budget_version=budget_version, user_model=self.user_model)
        rows = get_budget_vs_actual_data(budget_version)

        self.assertEqual(assignment.dimension_value, dimension_value)
        self.assertEqual(budget_version.status, 'approved')
        self.assertEqual(rows[0]['budget_amount'], Decimal('100.00'))

    def test_straight_line_depreciation_schedule(self):
        entity_model = self.get_random_entity_model()
        periods = [
            AccountingPeriodModel.objects.create(
                entity_model=entity_model,
                fiscal_year=2026,
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
            for period, start_date, end_date in [
                (1, date(2026, 1, 1), date(2026, 1, 31)),
                (2, date(2026, 2, 1), date(2026, 2, 28)),
                (3, date(2026, 3, 1), date(2026, 3, 31)),
            ]
        ]
        category = AssetCategoryModel.objects.create(
            entity_model=entity_model,
            name='Equipment',
            asset_account=self.get_random_account(entity_model=entity_model),
            depreciation_account=self.get_random_account(entity_model=entity_model),
            accumulated_depreciation_account=self.get_random_account(entity_model=entity_model),
        )
        method = DepreciationMethodModel.objects.create(
            entity_model=entity_model,
            name='Straight line 3 months',
            useful_life_months=3,
        )
        fixed_asset = FixedAssetModel.objects.create(
            entity_model=entity_model,
            name='Laptop',
            category=category,
            depreciation_method=method,
            acquisition_date=periods[0].start_date,
            acquisition_cost=Decimal('300.00'),
        )

        schedule = create_straight_line_depreciation_schedule(fixed_asset=fixed_asset)

        self.assertEqual(len(schedule), 3)
        self.assertEqual(schedule[0].depreciation_amount, Decimal('100.00'))
