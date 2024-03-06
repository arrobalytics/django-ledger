from decimal import Decimal
from random import choice, randint

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Count
from django.db.utils import IntegrityError

from django_ledger.forms.transactions import (
    get_transactionmodel_formset_class,
    TransactionModelForm,
    TransactionModelFormSet
)
from django_ledger.io.io_core import get_localdate
from django_ledger.models import (
    TransactionModel, EntityModel, AccountModel, LedgerModel, JournalEntryModel,
    TransactionModelValidationError, JournalEntryValidationError
)
from django_ledger.tests.base import DjangoLedgerBaseTest

UserModel = get_user_model()


class TransactionModelTest(DjangoLedgerBaseTest):

    def test_invalid_balance(self):
        entity_model = self.get_random_entity_model()
        txs_model = self.get_random_transaction(entity_model=entity_model)

        # transaction model does not allow for negative balances
        txs_model.amount = Decimal('-100.00')

        with self.assertRaises(ValidationError):
            txs_model.full_clean()


class TransactionModelFormTest(DjangoLedgerBaseTest):

    def test_valid_data(self):
        entity_model: EntityModel = self.get_random_entity_model()

        account_model = str(self.get_random_account(entity_model=entity_model, balance_type='credit').uuid),
        random_tx_type = choice([tx_type[0] for tx_type in TransactionModel.TX_TYPE])

        form_data = {
            'account': account_model[0],
            'tx_type': random_tx_type,
            'amount': Decimal(randint(10000, 99999)),
            'description': 'Bought Something ...'
        }

        form = TransactionModelForm(form_data)

        self.assertTrue(form.is_valid(), msg=f'Form is invalid with error: {form.errors}')
        with self.assertRaises(IntegrityError):
            form.save()

    def test_invalid_tx_type(self):
        account_model = choice(AccountModel.objects.filter(balance_type='credit'))
        form = TransactionModelForm({
            'account': account_model,
            'tx_type': 'crebit patty',
        })
        self.assertFalse(form.is_valid(), msg='tx_type other than credit / debit shouldn\'t be valid')

    def test_blank_data(self):
        form = TransactionModelForm()
        self.assertFalse(form.is_valid(), msg='Form without data is supposed to be invalid')

    def test_invalid_account(self):
        with self.assertRaises(ObjectDoesNotExist):
            form = TransactionModelForm({
                'account': 'Asset',
            })
            form.is_valid()


class TransactionModelFormSetTest(DjangoLedgerBaseTest):

    def get_random_txs_formsets(self,
                                entity_model: EntityModel,
                                ledger_model: LedgerModel = None,
                                je_model: JournalEntryModel = None) -> TransactionModelFormSet:
        """
        Returns a TransactionModelFormSet with prefilled form data.
        """

        if ledger_model:
            # if ledger model provided, get a je_model from provided ledger model...
            je_model: JournalEntryModel = self.get_random_je(
                entity_model=entity_model,
                ledger_model=ledger_model
            ) if not je_model else je_model

        else:

            # get a journal entry that has transactions...
            je_model = JournalEntryModel.objects.for_entity(
                entity_slug=entity_model,
                user_model=self.user_model
            ).annotate(
                txs_count=Count('transactionmodel')).filter(
                txs_count__gt=0).order_by('-timestamp').first()

        TransactionModelFormSet = get_transactionmodel_formset_class(journal_entry_model=je_model)

        txs_formset = TransactionModelFormSet(
            entity_slug=entity_model.slug,
            user_model=self.user_model,
            je_model=je_model,
            ledger_pk=je_model.ledger_id,
        )
        return txs_formset

    def test_valid_formset(self):
        """
        Saved Transaction instances should have identical detail with initial formset.
        """
        entity_model: EntityModel = self.get_random_entity_model()
        ledger_model: LedgerModel = self.get_random_ledger(entity_model=entity_model)
        je_model: JournalEntryModel = self.get_random_je(entity_model=entity_model, ledger_model=ledger_model)
        credit_account: AccountModel = self.get_random_account(entity_model=entity_model, balance_type='credit')
        debit_account: AccountModel = self.get_random_account(entity_model=entity_model, balance_type='debit')
        transaction_amount = Decimal.from_float(randint(10000, 99999))

        txs_formset = self.get_random_txs_formsets(
            entity_model=entity_model,
            je_model=je_model,
            ledger_model=ledger_model
        )

        self.assertTrue(
            txs_formset.is_valid(),
            msg=f"Formset is not valid, error: {txs_formset.errors}")

        txs_instances = txs_formset.save(commit=False)
        for txs in txs_instances:
            if not txs.journal_entry_id:
                txs.journal_entry_id = je_model.uuid

        txs_instances = txs_formset.save()
        for txs in txs_instances:
            if txs.tx_type == 'credit':
                self.assertEqual(
                    txs.account, credit_account,
                    msg=f'Saved Transaction record has mismatched Credit Account from the submitted formset. Saved:{txs.account} | form:{credit_account}')

            elif txs.tx_type == 'debit':
                self.assertEqual(
                    txs.account, debit_account,
                    msg=f'Saved Transaction record has mismatched Debit Account from the submitted formset. Saved:{txs.account} | form:{debit_account}')

            self.assertEqual(
                txs.amount, Decimal(transaction_amount),
                msg=f'Saved Transaction record has mismatched total amount from the submitted formset. Saved:{txs.amount} | form:{transaction_amount}')

    def test_imbalance_transactions(self):
        """
        Imbalanced Transactions should be invalid.
        """
        entity_model: EntityModel = self.get_random_entity_model()

        txs_formset = self.get_random_txs_formsets(entity_model=entity_model)

        self.assertFalse(
            txs_formset.is_valid(),
            msg=f"Formset is supposed to be invalid because of imbalance transaction"
        )

    def test_je_locked(self):
        """
        Transaction on locked a locked Journal Entry should fail.
        """
        entity_model: EntityModel = self.get_random_entity_model()
        ledger_model: LedgerModel = self.get_random_ledger(
            entity_model=entity_model
        )

        je_model: JournalEntryModel = self.get_random_je(
            entity_model=entity_model,
            ledger_model=ledger_model
        )
        je_model.mark_as_locked(commit=True, raise_exception=False)

        self.assertTrue(je_model.is_locked())
        txs_model = je_model.transactionmodel_set.all().first()
        txs_model.amount += Decimal.from_float(1.00)

        with self.assertRaises(TransactionModelValidationError):
            txs_model.save()

        with self.assertRaises(
                TransactionModelValidationError,
                msg=f'Cannot create transaction on locked Journal Entry'
        ):
            je_model.transactionmodel_set.create(
                amount=Decimal.from_float(100.00),
                account=self.get_random_account(entity_model=entity_model, balance_type='debit')
            )

    def test_ledger_lock(self):
        """
        Transaction on locked a locked Ledger should fail.
        """
        entity_model: EntityModel = self.get_random_entity_model()
        ledger_model = self.get_random_ledger(entity_model=entity_model)
        ledger_model.post(commit=True, raise_exception=False)
        self.assertTrue(ledger_model.is_posted())
        ledger_model.lock(commit=True, raise_exception=False)
        self.assertTrue(ledger_model.is_locked())

        with self.assertRaises(
                JournalEntryValidationError,
                msg='Cannot create Journal Entries on locked ledgers.'
        ):
            ledger_model.journal_entries.create(
                timestamp=get_localdate(),
                description='Test Journal Entry'
            )

        je_model = ledger_model.journal_entries.first()

        with self.assertRaises(
                JournalEntryValidationError,
                msg='Cannot unpost journal entry on locked ledgers'
        ):
            je_model.mark_as_unposted(commit=True, raise_exception=True)


class GetTransactionModelFormSetClassTest(DjangoLedgerBaseTest):

    def test_unlocked_journal_entry_formset(self):
        """
        The Formset will contain 6 extra forms & delete fields if Journal Entry is unlocked.
        """
        entity_model: EntityModel = self.get_random_entity_model()
        ledger_model: LedgerModel = self.get_random_ledger(entity_model=entity_model)
        je_model: JournalEntryModel = self.get_random_je(entity_model=entity_model, ledger_model=ledger_model)
        je_model.mark_as_unlocked(commit=True)

        transaction_model_form_set = get_transactionmodel_formset_class(journal_entry_model=je_model)
        txs_formset = transaction_model_form_set(
            user_model=self.user_model,
            je_model=je_model,
            ledger_pk=ledger_model,
            entity_slug=entity_model.slug,
        )

        self.assertTrue(not je_model.is_locked(),
                        msg="At this point in this test case, Journal Entry should be unlocked.")

        delete_field = '<input type="checkbox" name="form-0-DELETE" id="id_form-0-DELETE">'
        self.assertInHTML(
            delete_field,
            txs_formset.as_table(),
            msg_prefix='Transactions Formset with unlocked Journal Entry should have `can_delete` enabled'
        )

        self.assertEqual(len(txs_formset), 6,
                         msg='Transactions Formset with unlocked Journal Entry should have 6 extras')

    def test_locked_journal_entry_formset(self):
        """
        The Formset will contain no extra forms & only forms with Transaction if Journal Entry is locked.
        """
        entity_model: EntityModel = self.get_random_entity_model()
        ledger_model: LedgerModel = self.get_random_ledger(entity_model=entity_model)
        je_model: JournalEntryModel = self.get_random_je(entity_model=entity_model, ledger_model=ledger_model)
        # transaction_pairs = randint(1, 12)
        # self.get_random_transactions(entity_model=entity_model, je_model=je_model,
        #                              pairs=transaction_pairs)  # Fill Journal Entry with Transactions

        je_model.mark_as_locked(commit=True)
        self.assertTrue(
            je_model.is_locked(),
            msg="Journal Entry should be locked in this test case")

        transaction_model_form_set = get_transactionmodel_formset_class(journal_entry_model=je_model)

        txs_formset = transaction_model_form_set(
            user_model=self.user_model,
            je_model=je_model,
            ledger_pk=ledger_model,
            entity_slug=entity_model.slug,
            queryset=je_model.transactionmodel_set.all().order_by('account__code')
        )

        self.assertEqual(
            len(txs_formset), (je_model.transactionmodel_set.count()),  # Convert pairs to total count
            msg="Transactions Formset with unlocked Journal Entry did not match the expected count")
