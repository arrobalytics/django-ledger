"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Characterization tests for EntityDataGenerator.

These tests pin down what the sample data generator produces today. Each scenario seeds random and Faker, builds a
new entity, runs populate_entity() with fixed dates, and compares the totals of what was created against numbers
recorded from the current generator: how many vendors, customers, documents, journal entries and transactions it
makes, what the documents add up to, and the balances that end up on key accounts. Two seeds and two sizes are
covered, so a change to the draw order or to any document flow shows up as a changed number.

The expected numbers describe current behavior, not a specification. When a later release changes the generator on
purpose, the email for that patch lists the scenarios that moved and the numbers here are updated in the same patch.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.test import TestCase

from django_ledger.io.io_generator import EntityDataGenerator
from django_ledger.io.roles import (
    ASSET_CA_CASH,
    ASSET_CA_RECEIVABLES,
    EQUITY_CAPITAL,
    LIABILITY_CL_ACC_PAYABLE,
)
from django_ledger.models import (
    BankAccountModel,
    BillModel,
    CustomerModel,
    EntityModel,
    EntityUnitModel,
    EstimateModel,
    InvoiceModel,
    ItemModel,
    JournalEntryModel,
    PurchaseOrderModel,
    TransactionModel,
    UnitOfMeasureModel,
    VendorModel,
)
from django_ledger.tests.mixins import SeededTestMixIn, requires_faker

UserModel = get_user_model()

ZERO: Decimal = Decimal('0.00')
START_DTTM: datetime = datetime(2024, 1, 2, 9, 30, tzinfo=ZoneInfo('UTC'))
DAYS_FORWARD: int = 120
CAPITAL_CONTRIBUTION: Decimal = Decimal('50000.00')


@dataclass(frozen=True)
class GeneratorScenario:
    """
    One generator run: the seed used for random and Faker, and the number of documents asked for.
    """

    seed: int
    tx_quantity: int

    @property
    def label(self) -> str:
        """
        A short name for the scenario, used in subtest output.
        """
        return f'seed {self.seed}, tx_quantity {self.tx_quantity}'


SMALL_SEED_A = GeneratorScenario(seed=101, tx_quantity=4)
LARGE_SEED_A = GeneratorScenario(seed=101, tx_quantity=12)
SMALL_SEED_B = GeneratorScenario(seed=202, tx_quantity=4)
LARGE_SEED_B = GeneratorScenario(seed=202, tx_quantity=12)

SCENARIOS: tuple[GeneratorScenario, ...] = (SMALL_SEED_A, LARGE_SEED_A, SMALL_SEED_B, LARGE_SEED_B)

EXPECTED_AGGREGATES: dict[GeneratorScenario, dict[str, int | Decimal]] = {
    SMALL_SEED_A: {
        'vendors': 18,
        'customers': 17,
        'bank_accounts': 2,
        'entity_units': 4,
        'units_of_measure': 6,
        'items': 128,
        'estimates': 4,
        'purchase_orders': 4,
        'bills': 5,
        'bills_paid': 2,
        'invoices': 4,
        'invoices_paid': 0,
        'estimate_revenue': Decimal('4268.42'),
        'po_amount': Decimal('16222.84'),
        'bill_amount_due': Decimal('5567.49'),
        'bill_amount_paid': Decimal('1985.82'),
        'invoice_amount_due': Decimal('1918.02'),
        'invoice_amount_paid': Decimal('0.00'),
        'journal_entries': 14,
        'posted_journal_entries': 14,
        'transactions': 36,
        'posted_debits': Decimal('55565.27'),
        'posted_credits': Decimal('55565.27'),
        'cash_balance': Decimal('48014.18'),
        'receivables_balance': Decimal('1288.97'),
        'payables_balance': Decimal('0.00'),
        'capital_balance': Decimal('50000.00'),
    },
    LARGE_SEED_A: {
        'vendors': 18,
        'customers': 17,
        'bank_accounts': 2,
        'entity_units': 4,
        'units_of_measure': 6,
        'items': 128,
        'estimates': 12,
        'purchase_orders': 12,
        'bills': 16,
        'bills_paid': 5,
        'invoices': 12,
        'invoices_paid': 1,
        'estimate_revenue': Decimal('15073.05'),
        'po_amount': Decimal('65993.10'),
        'bill_amount_due': Decimal('37313.68'),
        'bill_amount_paid': Decimal('7483.87'),
        'invoice_amount_due': Decimal('10501.05'),
        'invoice_amount_paid': Decimal('1299.94'),
        'journal_entries': 31,
        'posted_journal_entries': 31,
        'transactions': 80,
        'posted_debits': Decimal('78161.74'),
        'posted_credits': Decimal('78161.74'),
        'cash_balance': Decimal('43816.07'),
        'receivables_balance': Decimal('885.64'),
        'payables_balance': Decimal('9159.23'),
        'capital_balance': Decimal('50000.00'),
    },
    SMALL_SEED_B: {
        'vendors': 16,
        'customers': 15,
        'bank_accounts': 2,
        'entity_units': 4,
        'units_of_measure': 6,
        'items': 127,
        'estimates': 4,
        'purchase_orders': 4,
        'bills': 4,
        'bills_paid': 2,
        'invoices': 4,
        'invoices_paid': 0,
        'estimate_revenue': Decimal('6624.80'),
        'po_amount': Decimal('45449.90'),
        'bill_amount_due': Decimal('4177.29'),
        'bill_amount_paid': Decimal('2392.42'),
        'invoice_amount_due': Decimal('0.00'),
        'invoice_amount_paid': Decimal('0.00'),
        'journal_entries': 11,
        'posted_journal_entries': 11,
        'transactions': 28,
        'posted_debits': Decimal('54784.84'),
        'posted_credits': Decimal('54784.84'),
        'cash_balance': Decimal('47607.58'),
        'receivables_balance': Decimal('0.00'),
        'payables_balance': Decimal('0.00'),
        'capital_balance': Decimal('50000.00'),
    },
    LARGE_SEED_B: {
        'vendors': 16,
        'customers': 15,
        'bank_accounts': 2,
        'entity_units': 4,
        'units_of_measure': 6,
        'items': 127,
        'estimates': 12,
        'purchase_orders': 12,
        'bills': 13,
        'bills_paid': 4,
        'invoices': 12,
        'invoices_paid': 4,
        'estimate_revenue': Decimal('17478.56'),
        'po_amount': Decimal('92671.41'),
        'bill_amount_due': Decimal('16276.79'),
        'bill_amount_paid': Decimal('4507.99'),
        'invoice_amount_due': Decimal('4429.03'),
        'invoice_amount_paid': Decimal('3354.12'),
        'journal_entries': 35,
        'posted_journal_entries': 35,
        'transactions': 95,
        'posted_debits': Decimal('67714.75'),
        'posted_credits': Decimal('67714.75'),
        'cash_balance': Decimal('48846.13'),
        'receivables_balance': Decimal('0.00'),
        'payables_balance': Decimal('0.00'),
        'capital_balance': Decimal('50000.00'),
    },
}


class GeneratorAggregatesMixIn:
    """
    Runs the generator for a scenario and reads back the totals of what it created.
    """

    USERNAME: str = 'generator-characterization'

    @classmethod
    def get_admin_user(cls):
        """
        The user that administers every generated entity.
        """
        user_model, _ = UserModel.objects.get_or_create(username=cls.USERNAME)
        return user_model

    @classmethod
    def populate_scenario(cls, scenario: GeneratorScenario) -> EntityModel:
        """
        Creates an empty entity and fills it with the generator after seeding random and Faker with the scenario seed.
        """
        user_model = cls.get_admin_user()
        entity_model = EntityModel.create_entity(
            name=f'Generator Characterization {scenario.seed} {scenario.tx_quantity}',
            use_accrual_method=True,
            fy_start_month=1,
            admin=user_model,
        )
        cls.seed_random_data(scenario.seed)
        generator = EntityDataGenerator(
            user_model=user_model,
            entity_model=entity_model,
            start_dttm=START_DTTM,
            capital_contribution=CAPITAL_CONTRIBUTION,
            days_forward=DAYS_FORWARD,
            tx_quantity=scenario.tx_quantity,
        )
        generator.populate_entity()
        return entity_model

    @staticmethod
    def sum_of(queryset, field_name: str) -> Decimal:
        """
        The sum of one decimal field over a queryset, rounded to cents, with zero for an empty queryset.
        """
        total = queryset.aggregate(total=Sum(field_name))['total']
        return ZERO if total is None else total.quantize(ZERO)

    @classmethod
    def net_debit_balance(cls, txs_qs, role: str) -> Decimal:
        """
        Debits minus credits on the posted transactions of every account with the given role.
        """
        role_qs = txs_qs.filter(account__role=role)
        debits = cls.sum_of(role_qs.filter(tx_type=TransactionModel.DEBIT), 'amount')
        credits = cls.sum_of(role_qs.filter(tx_type=TransactionModel.CREDIT), 'amount')
        return debits - credits

    @classmethod
    def get_aggregates(cls, entity_model: EntityModel) -> dict[str, int | Decimal]:
        """
        Counts, document totals and account balances for everything the generator created for one entity.
        """
        bills_qs = BillModel.objects.filter(entity_model=entity_model)
        invoices_qs = InvoiceModel.objects.filter(entity_model=entity_model)
        po_qs = PurchaseOrderModel.objects.filter(entity=entity_model)
        estimates_qs = EstimateModel.objects.filter(entity=entity_model)
        je_qs = JournalEntryModel.objects.filter(ledger__entity=entity_model)
        txs_qs = TransactionModel.objects.filter(journal_entry__ledger__entity=entity_model)
        posted_txs_qs = txs_qs.filter(journal_entry__posted=True)

        return {
            'vendors': VendorModel.objects.filter(entity_model=entity_model).count(),
            'customers': CustomerModel.objects.filter(entity_model=entity_model).count(),
            'bank_accounts': BankAccountModel.objects.filter(entity_model=entity_model).count(),
            'entity_units': EntityUnitModel.objects.filter(entity=entity_model).count(),
            'units_of_measure': UnitOfMeasureModel.objects.filter(entity=entity_model).count(),
            'items': ItemModel.objects.filter(entity=entity_model).count(),
            'estimates': estimates_qs.count(),
            'purchase_orders': po_qs.count(),
            'bills': bills_qs.count(),
            'bills_paid': bills_qs.filter(bill_status=BillModel.BILL_STATUS_PAID).count(),
            'invoices': invoices_qs.count(),
            'invoices_paid': invoices_qs.filter(invoice_status=InvoiceModel.INVOICE_STATUS_PAID).count(),
            'estimate_revenue': cls.sum_of(estimates_qs, 'revenue_estimate'),
            'po_amount': cls.sum_of(po_qs, 'po_amount'),
            'bill_amount_due': cls.sum_of(bills_qs, 'amount_due'),
            'bill_amount_paid': cls.sum_of(bills_qs, 'amount_paid'),
            'invoice_amount_due': cls.sum_of(invoices_qs, 'amount_due'),
            'invoice_amount_paid': cls.sum_of(invoices_qs, 'amount_paid'),
            'journal_entries': je_qs.count(),
            'posted_journal_entries': je_qs.filter(posted=True).count(),
            'transactions': txs_qs.count(),
            'posted_debits': cls.sum_of(posted_txs_qs.filter(tx_type=TransactionModel.DEBIT), 'amount'),
            'posted_credits': cls.sum_of(posted_txs_qs.filter(tx_type=TransactionModel.CREDIT), 'amount'),
            'cash_balance': cls.net_debit_balance(posted_txs_qs, ASSET_CA_CASH),
            'receivables_balance': cls.net_debit_balance(posted_txs_qs, ASSET_CA_RECEIVABLES),
            'payables_balance': -cls.net_debit_balance(posted_txs_qs, LIABILITY_CL_ACC_PAYABLE),
            'capital_balance': -cls.net_debit_balance(posted_txs_qs, EQUITY_CAPITAL),
        }


@requires_faker
class EntityDataGeneratorAggregatesTest(SeededTestMixIn, GeneratorAggregatesMixIn, TestCase):
    """
    The generator's output for two seeds and two sizes matches the totals recorded from the current generator.
    """

    ENTITIES: dict[GeneratorScenario, EntityModel] = {}

    @classmethod
    def setUpTestData(cls):
        cls.ENTITIES = {scenario: cls.populate_scenario(scenario) for scenario in SCENARIOS}

    def test_each_scenario_matches_the_recorded_totals(self):
        """Counts, document totals and balances match the recorded numbers for every scenario."""
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.label):
                self.assertEqual(self.get_aggregates(self.ENTITIES[scenario]), EXPECTED_AGGREGATES[scenario])

    def test_posted_debits_equal_posted_credits(self):
        """Every scenario posts as much in debits as in credits."""
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.label):
                aggregates = self.get_aggregates(self.ENTITIES[scenario])
                self.assertEqual(aggregates['posted_debits'], aggregates['posted_credits'])

    def test_capital_account_holds_the_capital_contribution(self):
        """The capital account ends with exactly the capital contribution passed to the generator."""
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.label):
                aggregates = self.get_aggregates(self.ENTITIES[scenario])
                self.assertEqual(aggregates['capital_balance'], CAPITAL_CONTRIBUTION)
