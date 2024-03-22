from django_ledger.models import EntityModelValidationError, AccountModel
from django_ledger.tests.base import DjangoLedgerBaseTest


class AccountModelTests(DjangoLedgerBaseTest):

    def test_no_default_coa(self):
        entity_model = self.create_entity_model()
        self.assertFalse(entity_model.has_default_coa(), msg='New entities do not had default coa')

        with self.assertRaises(EntityModelValidationError, msg='New entities do not have default coa'):
            entity_model.get_default_coa()

        self.assertEqual(entity_model.get_default_coa(raise_exception=False),
                         None,
                         msg='No exception should be raised when raise_exception is False')
