from django_ledger.io import roles
from django_ledger.models import EntityModelValidationError, ChartOfAccountModel, coa_default
from django_ledger.models.coa_default import DEFAULT_CHART_OF_ACCOUNTS
from django_ledger.tests.base import DjangoLedgerBaseTest


class ChartOfAccountsDefaultTests(DjangoLedgerBaseTest):

    def test_coa_default_builtin(self):
        coa_default.set_default_coa()
        entity_model = self.create_entity_model()
        default_coa_model = entity_model.create_chart_of_accounts(
            assign_as_default=True,
            commit=True,
            coa_name="Default CoA"
        )
        self.assertTrue(entity_model.has_default_coa(), msg='New entities do not have default coa')
        entity_model.populate_default_coa(activate_accounts=True, coa_model=default_coa_model)
        self.assertEqual(default_coa_model.get_coa_accounts().count(), len(DEFAULT_CHART_OF_ACCOUNTS))

    def test_coa_set_default_coa(self):
        new_coa_default = [
            {'code': '1001', 'role': roles.ASSET_CA_CASH, 'balance_type': 'debit', 'name': 'Checking 1',
             'parent': None},
            {'code': '6999', 'role': roles.EXPENSE_OTHER, 'balance_type': 'debit', 'name': 'Miscellaneous Expense',
             'parent': None},
        ]
        coa_default.set_default_coa(new_coa_default)
        self.assertTrue(len(coa_default.get_default_coa()), len(new_coa_default))
        # now test with entity
        entity_model = self.create_entity_model()
        default_coa_model = entity_model.create_chart_of_accounts(
            assign_as_default=True,
            commit=True,
            coa_name="Default CoA"
        )
        self.assertTrue(entity_model.has_default_coa(), msg='New entities do not have default coa')
        entity_model.populate_default_coa(activate_accounts=True, coa_model=default_coa_model)
        self.assertEqual(default_coa_model.get_coa_accounts().count(), len(new_coa_default))

