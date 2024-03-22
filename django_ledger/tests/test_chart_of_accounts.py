from django_ledger.models import EntityModelValidationError, ChartOfAccountModel
from django_ledger.tests.base import DjangoLedgerBaseTest


class ChartOfAccountsTests(DjangoLedgerBaseTest):

    def test_no_default_coa(self):
        entity_model = self.create_entity_model()
        self.assertFalse(entity_model.has_default_coa(), msg='New entities do not had default coa')

        with self.assertRaises(EntityModelValidationError, msg='New entities do not have default coa'):
            entity_model.get_default_coa()

        self.assertEqual(entity_model.get_default_coa(raise_exception=False), None,
                         msg='No exception should be raised when raise_exception is False')

    def test_set_default_coa(self):
        entity_model = self.create_entity_model()
        coa_model = entity_model.create_chart_of_accounts(coa_name='Now CoA For Testing', assign_as_default=False)
        self.assertTrue(isinstance(coa_model, ChartOfAccountModel))
        self.assertFalse(entity_model.has_default_coa())

    def test_create_coa(self):
        entity_model = self.create_entity_model()
        coa_model = entity_model.create_chart_of_accounts(coa_name='Now CoA For Testing', assign_as_default=False)

        account_model_qs = coa_model.accountmodel_set.all()

        account_count = account_model_qs.count()
        self.assertTrue(account_count, 7)

        ROOT_ACCOUNT_CODES = [
            '00000000',  # root_account
            '01000000',  # asset account root
            '02000000',  # liability accounts root
            '03000000',  # capital accounts root
            '04000000',  # income accounts root
            '05000000',  # cogs accounts root
            '06000000',  # expenses accounts root
        ]

        for account in account_model_qs:
            self.assertTrue(account.code in ROOT_ACCOUNT_CODES)

    # todo: cannot transact on root account
    # todo: validate parent/child relationship...
