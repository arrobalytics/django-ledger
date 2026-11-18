"""High-level API behavior tests for EntityModel chart of accounts APIs."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io.roles import ASSET_CA_CASH, DEBIT, EXPENSE_OPERATIONAL
from django_ledger.models import AccountModel, ChartOfAccountModel
from django_ledger.models.entity import EntityModel, EntityModelValidationError


class EntityChartOfAccountsHighLevelAPITest(TestCase):
    """
    High-level behavior tests for the public Entity -> CoA -> Account setup API.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document small, deterministic business contracts that should
    remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_contract_user",
            email="api-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_contract_unrelated_user",
            email="api-contract-unrelated-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Contract Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_entity_with_default_coa(
        self,
        *,
        entity_name="API Contract Entity",
        coa_name="API Contract CoA",
    ):
        entity_model = self.create_entity(name=entity_name)
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=coa_name,
            commit=True,
            assign_as_default=True,
        )
        entity_model.refresh_from_db()
        return entity_model, coa_model

    def create_cash_account(
        self,
        entity_model,
        *,
        code="1010",
        name="API Contract Cash Account",
        coa_model=None,
        active=True,
        is_role_default=False,
        force_role_default=False,
    ):
        return entity_model.create_account(
            code=code,
            name=name,
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=active,
            coa_model=coa_model,
            is_role_default=is_role_default,
            force_role_default=force_role_default,
        )

    def create_expense_account(
        self,
        entity_model,
        *,
        code="6010",
        name="API Contract Expense Account",
        coa_model=None,
        active=True,
    ):
        return entity_model.create_account(
            code=code,
            name=name,
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=active,
            coa_model=coa_model,
        )

    def test_create_entity_produces_usable_accounting_entity(self):
        entity_model = self.create_entity()

        self.assertIsNotNone(entity_model.uuid)
        self.assertEqual(entity_model.name, "API Contract Entity")
        self.assertEqual(entity_model.admin, self.user)
        self.assertTrue(entity_model.accrual_method)
        self.assertEqual(entity_model.fy_start_month, 1)

    def test_create_chart_of_accounts_can_assign_default_coa(self):
        entity_model = self.create_entity()

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        entity_model.refresh_from_db()

        self.assertIsNotNone(coa_model.uuid)
        self.assertEqual(coa_model.name, "API Contract CoA")
        self.assertEqual(coa_model.entity_id, entity_model.uuid)
        self.assertTrue(coa_model.active)
        self.assertEqual(entity_model.default_coa_id, coa_model.uuid)

    def test_create_chart_of_accounts_returns_configured_chart_with_root_structure(self):
        entity_model = self.create_entity(name="API Entity CoA Orchestration Entity")

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Entity Orchestrated CoA",
            commit=True,
            assign_as_default=False,
        )

        self.assertIsInstance(coa_model, ChartOfAccountModel)
        self.assertEqual(coa_model.entity_id, entity_model.uuid)
        self.assertEqual(coa_model.name, "API Entity Orchestrated CoA")
        self.assertTrue(coa_model.slug)
        self.assertTrue(coa_model.is_configured())

        root_node = coa_model.get_coa_root_node()
        root_accounts_qs = coa_model.get_coa_root_accounts_qs()

        self.assertTrue(root_node.is_coa_root())
        self.assertTrue(root_accounts_qs.exists())
        self.assertTrue(all(account.is_root_account() for account in root_accounts_qs))

    def test_create_chart_of_accounts_configures_root_account_tree(self):
        entity_model = self.create_entity()

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        self.assertTrue(
            coa_model.is_configured(),
            "A CoA created through the high-level API should be configured.",
        )

        accounts_qs = AccountModel.objects.for_entity(entity_model)
        root_accounts_qs = accounts_qs.is_coa_root()

        self.assertGreater(
            root_accounts_qs.count(),
            0,
            "A configured CoA should include technical root accounts.",
        )

        for root_account in root_accounts_qs:
            self.assertTrue(root_account.locked)
            self.assertFalse(root_account.active)
            self.assertTrue(root_account.role_default)

    def test_create_account_adds_real_account_to_default_coa(self):
        entity_model, coa_model = self.create_entity_with_default_coa()

        account_model = entity_model.create_account(
            code="1010",
            name="API Contract Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )

        account_model.refresh_from_db()

        self.assertEqual(account_model.coa_model_id, coa_model.uuid)
        self.assertEqual(account_model.code, "1010")
        self.assertEqual(account_model.name, "API Contract Cash Account")
        self.assertEqual(account_model.role, ASSET_CA_CASH)
        self.assertEqual(account_model.balance_type, DEBIT)
        self.assertTrue(account_model.active)
        self.assertFalse(account_model.locked)
        self.assertFalse(account_model.is_root_account())
        self.assertTrue(account_model.can_transact())

    def test_default_entity_account_queryset_exposes_created_real_account(self):
        entity_model, _coa_model = self.create_entity_with_default_coa()

        account_model = entity_model.create_account(
            code="1020",
            name="API Contract Bank Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )

        default_coa_accounts = entity_model.get_default_coa_accounts()

        self.assertTrue(
            default_coa_accounts.filter(uuid=account_model.uuid).exists(),
            "EntityModel.get_default_coa_accounts() should expose accounts "
            "from the entity default CoA.",
        )

        self.assertFalse(
            AccountModel.objects.for_entity(entity_model)
            .is_coa_root()
            .filter(uuid=account_model.uuid)
            .exists(),
            "A real account created via the entity API should not be treated as "
            "a technical CoA root account.",
        )

    def test_default_coa_can_be_read_and_switched_by_model_or_slug(self):
        entity_model = self.create_entity()

        with self.assertRaises(EntityModelValidationError):
            entity_model.get_default_coa()

        self.assertIsNone(entity_model.get_default_coa(raise_exception=False))

        first_coa = entity_model.create_chart_of_accounts(
            coa_name="API First CoA",
            commit=True,
            assign_as_default=True,
        )
        second_coa = entity_model.create_chart_of_accounts(
            coa_name="API Second CoA",
            commit=True,
            assign_as_default=False,
        )

        entity_model.refresh_from_db()
        self.assertEqual(entity_model.get_default_coa(), first_coa)
        self.assertTrue(first_coa.is_default())
        self.assertFalse(second_coa.is_default())

        entity_model.set_default_coa(second_coa, commit=True)
        entity_model.refresh_from_db()
        second_coa.refresh_from_db()
        self.assertEqual(entity_model.get_default_coa(), second_coa)
        self.assertTrue(second_coa.is_default())

        entity_model.set_default_coa(first_coa.slug, commit=True)
        entity_model.refresh_from_db()
        first_coa.refresh_from_db()
        self.assertEqual(entity_model.get_default_coa(), first_coa)
        self.assertTrue(first_coa.is_default())

    def test_get_coa_model_qs_filters_by_entity_and_active_status(self):
        entity_model, active_coa = self.create_entity_with_default_coa(
            entity_name="API CoA Query Entity",
            coa_name="API Active CoA",
        )
        inactive_coa = entity_model.create_chart_of_accounts(
            coa_name="API Inactive CoA",
            commit=True,
            assign_as_default=False,
        )
        inactive_coa.active = False
        inactive_coa.save(update_fields=["active"])

        other_entity, other_coa = self.create_entity_with_default_coa(
            entity_name="API Other CoA Query Entity",
            coa_name="API Other Active CoA",
        )

        active_qs = entity_model.get_coa_model_qs(active=True)
        all_qs = entity_model.get_coa_model_qs(active=False)

        self.assertTrue(active_qs.filter(uuid=active_coa.uuid).exists())
        self.assertFalse(active_qs.filter(uuid=inactive_coa.uuid).exists())
        self.assertFalse(active_qs.filter(uuid=other_coa.uuid).exists())

        self.assertTrue(all_qs.filter(uuid=active_coa.uuid).exists())
        self.assertTrue(all_qs.filter(uuid=inactive_coa.uuid).exists())
        self.assertFalse(all_qs.filter(entity=other_entity).exists())

    def test_populate_default_coa_creates_default_accounts_once(self):
        entity_model = self.create_entity(name="API Populated Default CoA Entity")

        entity_model.populate_default_coa(activate_accounts=True)
        entity_model.refresh_from_db()

        coa_model = entity_model.get_default_coa()
        default_accounts = entity_model.get_default_coa_accounts(active=True)
        account_uuids = set(default_accounts.values_list("uuid", flat=True))

        self.assertIsNotNone(coa_model)
        self.assertTrue(coa_model.is_configured())
        self.assertGreater(len(account_uuids), 0)

        cash_account = entity_model.get_default_account_for_role(ASSET_CA_CASH)
        self.assertEqual(cash_account.coa_model_id, coa_model.uuid)
        self.assertEqual(cash_account.role, ASSET_CA_CASH)
        self.assertTrue(cash_account.role_default)
        self.assertTrue(cash_account.active)

        entity_model.populate_default_coa(activate_accounts=True)
        default_accounts_after_second_call = entity_model.get_default_coa_accounts(active=True)
        account_uuids_after_second_call = set(
            default_accounts_after_second_call.values_list("uuid", flat=True)
        )

        self.assertEqual(account_uuids_after_second_call, account_uuids)

    def test_entity_account_query_helpers_scope_accounts_by_default_and_explicit_coa(self):
        entity_model, default_coa = self.create_entity_with_default_coa(
            entity_name="API Account Scope Entity",
            coa_name="API Default Scope CoA",
        )
        default_account = self.create_cash_account(
            entity_model,
            code="1010",
            name="API Default Cash Account",
        )

        second_coa = entity_model.create_chart_of_accounts(
            coa_name="API Secondary Scope CoA",
            commit=True,
            assign_as_default=False,
        )
        second_account = self.create_cash_account(
            entity_model,
            code="1020",
            name="API Secondary Cash Account",
            coa_model=second_coa,
        )

        other_entity, _other_coa = self.create_entity_with_default_coa(
            entity_name="API Other Account Scope Entity",
            coa_name="API Other Scope CoA",
        )
        other_account = self.create_cash_account(
            other_entity,
            code="1010",
            name="API Other Cash Account",
        )

        default_accounts = entity_model.get_default_coa_accounts()
        self.assertTrue(default_accounts.filter(uuid=default_account.uuid).exists())
        self.assertFalse(default_accounts.filter(uuid=second_account.uuid).exists())
        self.assertFalse(default_accounts.filter(uuid=other_account.uuid).exists())

        second_coa_model, second_coa_accounts = entity_model.get_coa_accounts(
            coa_model=second_coa,
            return_coa_model=True,
        )
        self.assertEqual(second_coa_model, second_coa)
        self.assertTrue(second_coa_accounts.filter(uuid=second_account.uuid).exists())
        self.assertFalse(second_coa_accounts.filter(uuid=default_account.uuid).exists())

        all_entity_accounts = entity_model.get_all_accounts()
        self.assertTrue(all_entity_accounts.filter(uuid=default_account.uuid).exists())
        self.assertTrue(all_entity_accounts.filter(uuid=second_account.uuid).exists())
        self.assertFalse(all_entity_accounts.filter(uuid=other_account.uuid).exists())

        coa_qs, accounts_by_coa = entity_model.get_all_coa_accounts()
        self.assertTrue(coa_qs.filter(uuid=default_coa.uuid).exists())
        self.assertTrue(coa_qs.filter(uuid=second_coa.uuid).exists())
        self.assertFalse(coa_qs.filter(entity=other_entity).exists())
        self.assertTrue(accounts_by_coa[default_coa].filter(uuid=default_account.uuid).exists())
        self.assertTrue(accounts_by_coa[second_coa].filter(uuid=second_account.uuid).exists())

    def test_get_accounts_with_codes_accepts_string_list_and_set(self):
        entity_model, _coa_model = self.create_entity_with_default_coa(
            entity_name="API Account Codes Entity",
            coa_name="API Account Codes CoA",
        )
        cash_account = self.create_cash_account(
            entity_model,
            code="1010",
            name="API Cash Code Account",
        )
        expense_account = self.create_expense_account(
            entity_model,
            code="6010",
            name="API Expense Code Account",
        )

        account_from_string = entity_model.get_accounts_with_codes("1010")
        accounts_from_list = entity_model.get_accounts_with_codes(["1010", "6010"])
        accounts_from_set = entity_model.get_accounts_with_codes({"1010", "6010"})

        self.assertEqual(list(account_from_string), [cash_account])
        self.assertEqual(
            set(accounts_from_list.values_list("uuid", flat=True)),
            {cash_account.uuid, expense_account.uuid},
        )
        self.assertEqual(
            set(accounts_from_set.values_list("uuid", flat=True)),
            {cash_account.uuid, expense_account.uuid},
        )

    def test_get_default_account_for_role_returns_populated_role_default_account(self):
        entity_model = self.create_entity(name="API Role Default Entity")
        entity_model.populate_default_coa(activate_accounts=True)

        account_model = entity_model.get_default_account_for_role(ASSET_CA_CASH)

        self.assertEqual(account_model.role, ASSET_CA_CASH)
        self.assertTrue(account_model.role_default)
        self.assertEqual(account_model.coa_model_id, entity_model.default_coa_id)

    def test_validate_chart_of_accounts_for_entity_rejects_other_entity_coa(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            entity_name="API CoA Validation Entity",
            coa_name="API Valid CoA",
        )
        _other_entity, other_coa = self.create_entity_with_default_coa(
            entity_name="API Other CoA Validation Entity",
            coa_name="API Other CoA",
        )

        self.assertTrue(entity_model.validate_chart_of_accounts_for_entity(coa_model))
        self.assertFalse(
            entity_model.validate_chart_of_accounts_for_entity(
                other_coa,
                raise_exception=False,
            )
        )

        with self.assertRaises(EntityModelValidationError):
            entity_model.validate_chart_of_accounts_for_entity(other_coa)

    def test_validate_account_model_for_coa_rejects_account_from_other_coa(self):
        entity_model, default_coa = self.create_entity_with_default_coa(
            entity_name="API Account Validation Entity",
            coa_name="API Valid Account CoA",
        )
        default_account = self.create_cash_account(
            entity_model,
            code="1010",
            name="API Valid Account",
        )
        second_coa = entity_model.create_chart_of_accounts(
            coa_name="API Other Account CoA",
            commit=True,
            assign_as_default=False,
        )
        other_account = self.create_cash_account(
            entity_model,
            code="1020",
            name="API Other CoA Account",
            coa_model=second_coa,
        )

        self.assertTrue(
            entity_model.validate_account_model_for_coa(
                account_model=default_account,
                coa_model=default_coa,
            )
        )
        self.assertFalse(
            entity_model.validate_account_model_for_coa(
                account_model=other_account,
                coa_model=default_coa,
                raise_exception=False,
            )
        )

        with self.assertRaises(EntityModelValidationError):
            entity_model.validate_account_model_for_coa(
                account_model=other_account,
                coa_model=default_coa,
            )

    def test_create_chart_of_accounts_without_default_does_not_replace_existing_default(self):
        entity_model, first_coa = self.create_entity_with_default_coa(
            entity_name="API Entity Preserve Default CoA Entity",
            coa_name="API Entity Preserve Default First CoA",
        )

        second_coa = entity_model.create_chart_of_accounts(
            coa_name="API Entity Preserve Default Second CoA",
            commit=True,
            assign_as_default=False,
        )

        entity_model.refresh_from_db()
        first_coa.refresh_from_db()
        second_coa.refresh_from_db()

        self.assertEqual(entity_model.default_coa_id, first_coa.uuid)
        self.assertTrue(first_coa.is_default())
        self.assertFalse(second_coa.is_default())

    def test_entity_can_own_multiple_coas_and_queryset_exposes_each(self):
        entity_model, default_coa = self.create_entity_with_default_coa(
            entity_name="API Entity Multiple CoA Entity",
            coa_name="API Entity Multiple Default CoA",
        )
        second_coa = entity_model.create_chart_of_accounts(
            coa_name="API Entity Multiple Second CoA",
            commit=True,
            assign_as_default=False,
        )

        entity_coa_qs = ChartOfAccountModel.objects.for_entity(entity_model)

        self.assertTrue(entity_coa_qs.filter(uuid=default_coa.uuid).exists())
        self.assertTrue(entity_coa_qs.filter(uuid=second_coa.uuid).exists())
        self.assertEqual(
            [coa.uuid for coa in (default_coa, second_coa) if coa.is_default()],
            [default_coa.uuid],
        )

    def test_populate_default_coa_creates_known_default_accounts(self):
        entity_model = self.create_entity(name="API Entity Known Default CoA Entity")

        entity_model.populate_default_coa(activate_accounts=True)
        entity_model.refresh_from_db()

        default_accounts_qs = entity_model.get_default_coa_accounts(active=True)
        cash_account = default_accounts_qs.get(code="1010")
        expense_account = default_accounts_qs.get(code="6190")

        self.assertEqual(cash_account.role, ASSET_CA_CASH)
        self.assertEqual(cash_account.name, "Cash")
        self.assertEqual(cash_account.coa_model_id, entity_model.default_coa_id)

        self.assertEqual(expense_account.role, EXPENSE_OPERATIONAL)
        self.assertEqual(expense_account.name, "Office Expense")
        self.assertEqual(expense_account.coa_model_id, entity_model.default_coa_id)

    def test_entity_created_coa_is_visible_through_user_scoped_queryset(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            entity_name="API Entity CoA User Scope Entity",
            coa_name="API Entity CoA User Scope CoA",
        )

        entity_coa_qs = ChartOfAccountModel.objects.for_entity(entity_model)
        admin_qs = entity_coa_qs.for_user(self.user)
        unrelated_qs = entity_coa_qs.for_user(self.unrelated_user)

        self.assertTrue(admin_qs.filter(uuid=coa_model.uuid).exists())
        self.assertFalse(unrelated_qs.filter(uuid=coa_model.uuid).exists())

    def test_create_account_by_kwargs_uses_default_coa(self):
        entity_model, default_coa = self.create_entity_with_default_coa(
            entity_name="API Kwargs Account Entity",
            coa_name="API Kwargs Account CoA",
        )

        returned_coa, account_model = entity_model.create_account_by_kwargs(
            {
                "code": "1010",
                "name": "API Kwargs Cash Account",
                "role": ASSET_CA_CASH,
                "balance_type": DEBIT,
                "active": True,
            }
        )

        self.assertEqual(returned_coa, default_coa)
        self.assertEqual(account_model.coa_model_id, default_coa.uuid)
        self.assertEqual(account_model.code, "1010")
        self.assertEqual(account_model.name, "API Kwargs Cash Account")
        self.assertEqual(account_model.role, ASSET_CA_CASH)
        self.assertTrue(account_model.active)
        self.assertTrue(
            entity_model.get_default_coa_accounts().filter(uuid=account_model.uuid).exists()
        )

    def test_create_account_accepts_explicit_coa_uuid(self):
        entity_model, _default_coa = self.create_entity_with_default_coa(
            entity_name="API Explicit UUID Account Entity",
            coa_name="API Explicit UUID Default CoA",
        )
        explicit_coa = entity_model.create_chart_of_accounts(
            coa_name="API Explicit UUID CoA",
            commit=True,
            assign_as_default=False,
        )

        account_model = entity_model.create_account(
            code="1030",
            name="API Explicit UUID Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            coa_model=explicit_coa.uuid,
        )

        self.assertEqual(account_model.coa_model_id, explicit_coa.uuid)
        self.assertTrue(
            entity_model.get_coa_accounts(coa_model=explicit_coa)
            .filter(uuid=account_model.uuid)
            .exists()
        )
        self.assertFalse(
            entity_model.get_default_coa_accounts().filter(uuid=account_model.uuid).exists()
        )

    def test_create_account_accepts_explicit_coa_slug(self):
        entity_model, _default_coa = self.create_entity_with_default_coa(
            entity_name="API Explicit Slug Account Entity",
            coa_name="API Explicit Slug Default CoA",
        )
        explicit_coa = entity_model.create_chart_of_accounts(
            coa_name="API Explicit Slug CoA",
            commit=True,
            assign_as_default=False,
        )

        account_model = entity_model.create_account(
            code="1040",
            name="API Explicit Slug Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            coa_model=explicit_coa.slug,
        )

        self.assertEqual(account_model.coa_model_id, explicit_coa.uuid)
        self.assertTrue(
            entity_model.get_coa_accounts(coa_model=explicit_coa)
            .filter(uuid=account_model.uuid)
            .exists()
        )
        self.assertFalse(
            entity_model.get_default_coa_accounts().filter(uuid=account_model.uuid).exists()
        )

    def test_create_account_by_kwargs_accepts_explicit_coa_uuid(self):
        entity_model, _default_coa = self.create_entity_with_default_coa(
            entity_name="API Explicit UUID Kwargs Account Entity",
            coa_name="API Explicit UUID Kwargs Default CoA",
        )
        explicit_coa = entity_model.create_chart_of_accounts(
            coa_name="API Explicit UUID Kwargs CoA",
            commit=True,
            assign_as_default=False,
        )

        returned_coa, account_model = entity_model.create_account_by_kwargs(
            {
                "code": "1050",
                "name": "API Explicit UUID Kwargs Cash Account",
                "role": ASSET_CA_CASH,
                "balance_type": DEBIT,
                "active": True,
            },
            coa_model=explicit_coa.uuid,
        )

        self.assertEqual(returned_coa, explicit_coa)
        self.assertEqual(account_model.coa_model_id, explicit_coa.uuid)
        self.assertTrue(
            entity_model.get_coa_accounts(coa_model=explicit_coa)
            .filter(uuid=account_model.uuid)
            .exists()
        )
        self.assertFalse(
            entity_model.get_default_coa_accounts().filter(uuid=account_model.uuid).exists()
        )

    def test_create_account_by_kwargs_accepts_explicit_coa_slug(self):
        entity_model, _default_coa = self.create_entity_with_default_coa(
            entity_name="API Explicit Slug Kwargs Account Entity",
            coa_name="API Explicit Slug Kwargs Default CoA",
        )
        explicit_coa = entity_model.create_chart_of_accounts(
            coa_name="API Explicit Slug Kwargs CoA",
            commit=True,
            assign_as_default=False,
        )

        returned_coa, account_model = entity_model.create_account_by_kwargs(
            {
                "code": "1060",
                "name": "API Explicit Slug Kwargs Cash Account",
                "role": ASSET_CA_CASH,
                "balance_type": DEBIT,
                "active": True,
            },
            coa_model=explicit_coa.slug,
        )

        self.assertEqual(returned_coa, explicit_coa)
        self.assertEqual(account_model.coa_model_id, explicit_coa.uuid)
        self.assertTrue(
            entity_model.get_coa_accounts(coa_model=explicit_coa)
            .filter(uuid=account_model.uuid)
            .exists()
        )
        self.assertFalse(
            entity_model.get_default_coa_accounts().filter(uuid=account_model.uuid).exists()
        )
