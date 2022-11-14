"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import date, timedelta
from decimal import Decimal
from itertools import groupby
from random import randint, random, choice, choices
from string import ascii_uppercase
from typing import Union

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.timezone import localtime, localdate

from django_ledger.io.roles import (INCOME_OPERATIONAL, ASSET_CA_INVENTORY, COGS, ASSET_CA_CASH, ASSET_CA_PREPAID,
                                    LIABILITY_CL_DEFERRED_REVENUE, EXPENSE_REGULAR, EQUITY_CAPITAL,
                                    ASSET_CA_RECEIVABLES, LIABILITY_CL_ACC_PAYABLE)
from django_ledger.models import EntityModel, TransactionModel, AccountModel, VendorModel, CustomerModel, \
    EntityUnitModel, BankAccountModel, LedgerModel, UnitOfMeasureModel, ItemModel, \
    BillModel, ItemTransactionModel, PurchaseOrderModel, InvoiceModel, \
    create_entity_unit_slug, EstimateModel
from django_ledger.utils import (generate_random_sku, generate_random_upc, generate_random_item_id)

try:
    from faker import Faker
    from faker.providers import company, address, phone_number, bank

    FAKER_IMPORTED = True
except ImportError:
    FAKER_IMPORTED = False


class EntityDataGenerator:

    def __init__(self,
                 user_model,
                 entity_model: Union[EntityModel, str],
                 start_date: date,
                 capital_contribution: Decimal,
                 days_forward: int,
                 tx_quantity: int = 25):

        assert isinstance(entity_model, (EntityModel, str)), 'Must pass an instance of EntityModel or str'
        assert capital_contribution > 0, 'Capital contribution must be greater than 0'

        if not FAKER_IMPORTED:
            raise ImproperlyConfigured('Must install Faker library to generate random data.')

        self.fk = Faker(['en_US'])
        self.fk.add_provider(company)
        self.fk.add_provider(address)
        self.fk.add_provider(phone_number)
        self.fk.add_provider(bank)

        self.start_date: date = start_date
        self.local_date = localdate()
        self.tx_quantity = tx_quantity
        self.localtime = localtime()
        self.COUNT_INVENTORY = True
        self.DAYS_FORWARD = days_forward

        self.entity_model: EntityModel = entity_model
        self.capital_contribution = capital_contribution
        self.user_model = user_model

        self.is_accruable_probability = 0.2
        self.is_paid_probability = 0.90

        self.vendor_models = None
        self.customer_models = None
        self.bank_account_models = None
        self.entity_unit_models = None
        self.uom_models = None
        self.expense_models = None
        self.product_and_services_models = None
        self.inventory_models = None

        self.account_models = None
        self.accounts_by_role = None

        self.COUNTRY = 'US'
        self.NB_UNITS: int = 4

        self.PRODUCTS_MIN = 20
        self.PRODUCTS_MAX = 40
        self.MIN_DAYS_FORWARD = 1
        self.MAX_DAYS_FORWARD = 8

    def populate_entity(self):

        txs_qs = TransactionModel.objects.for_entity(
            entity_slug=self.entity_model,
            user_model=self.user_model
        )

        if txs_qs.count() > 0:
            raise ValidationError(
                f'Cannot populate random data on {self.entity_model.name} because it already has existing Transactions')

        self.account_models = AccountModel.on_coa.for_entity_available(
            entity_slug=self.entity_model.slug,
            user_model=self.user_model
        ).order_by('role')

        self.accounts_by_role = {
            g: list(v) for g, v in groupby(self.account_models, key=lambda a: a.role)
        }

        self.create_vendors()
        self.create_customers()
        self.create_entity_units()
        self.create_bank_accounts()
        self.create_uom_models()
        self.create_products()
        self.create_expenses()
        self.create_inventories()
        self.fund_entity()

        count_inventory = True

        for i in range(self.tx_quantity):
            start_dttm = self.start_date + timedelta(days=randint(0, self.DAYS_FORWARD))
            self.create_estimates(date_draft=start_dttm)

            if random() > 0.4:
                self.create_po(date_draft=start_dttm)
                self.recount_inventory()
                self.update_products()

            self.create_bill(date_draft=start_dttm)
            self.create_invoice(date_draft=start_dttm)

    def get_next_date(self, prev_date: date = None) -> date:
        if not prev_date:
            prev_date = self.start_date
        next_date = prev_date + timedelta(days=randint(
            self.MIN_DAYS_FORWARD,
            self.MAX_DAYS_FORWARD
        ))
        if next_date > self.local_date:
            next_date = self.local_date
        return next_date

    def create_entity_units(self, nb_units: int = None):
        nb_units = self.NB_UNITS if not nb_units else nb_units

        if nb_units:
            assert nb_units >= 0, 'Number of unite must be greater than 0'

        entity_unit_models = [
            EntityUnitModel.add_root(
                name=f'Unit {u}',
                slug=create_entity_unit_slug(
                    name=f'{self.entity_model.name}-Unit {u}'),
                entity=self.entity_model,
                document_prefix=''.join(choices(ascii_uppercase, k=3))
            ) for u in range(nb_units)
        ]

        self.entity_unit_models = self.entity_model.entityunitmodel_set.all()

    def create_vendors(self):
        vendor_count = randint(10, 20)
        vendor_models = [
            VendorModel(
                vendor_name=self.fk.name() if random() > .7 else self.fk.company(),
                entity=self.entity_model,
                address_1=self.fk.street_address(),
                address_2=self.fk.building_number() if random() < .2 else None,
                city=self.fk.city(),
                state=self.fk.state_abbr(),
                zip_code=self.fk.postcode(),
                phone=self.fk.phone_number(),
                country=self.COUNTRY,
                email=self.fk.email(),
                website=self.fk.url(),
                active=True,
                hidden=False,
                description='A cool vendor description.'
            ) for _ in range(vendor_count)
        ]

        for vendor in vendor_models:
            vendor.full_clean()

        self.vendor_models = VendorModel.objects.bulk_create(vendor_models, ignore_conflicts=True)

    def create_customers(self):
        customer_count = randint(10, 20)
        customer_models = [
            CustomerModel(
                customer_name=self.fk.name() if random() > .2 else self.fk.company(),
                entity=self.entity_model,
                address_1=self.fk.street_address() + self.fk.street_suffix(),
                address_2=self.fk.building_number() if random() > .2 else None,
                city=self.fk.city(),
                state=self.fk.state_abbr(),
                zip_code=self.fk.postcode(),
                country=self.COUNTRY,
                phone=self.fk.phone_number(),
                email=self.fk.email(),
                website=self.fk.url(),
                active=True,
                hidden=False,
                description=f'A cool customer description. We love customers!'
            ) for _ in range(customer_count)
        ]

        for customer in customer_models:
            customer.full_clean()

        self.customer_models = CustomerModel.objects.bulk_create(customer_models, ignore_conflicts=True)

    def create_bank_accounts(self):
        bank_account_models = [
            BankAccountModel(name=f'{self.entity_model.name} Checking Account',
                             account_number=self.fk.bban(),
                             routing_number=self.fk.swift11(),
                             aba_number=self.fk.swift(),
                             account_type='checking',
                             active=True,
                             cash_account=choice(self.accounts_by_role['asset_ca_cash']),
                             entity_model=self.entity_model),
            BankAccountModel(name=f'{self.entity_model.name} Savings Account',
                             account_number=self.fk.bban(),
                             routing_number=self.fk.swift11(),
                             aba_number=self.fk.swift(),
                             active=True,
                             account_type='savings',
                             cash_account=choice(self.accounts_by_role['asset_ca_cash']),
                             entity_model=self.entity_model),
        ]
        for ba in bank_account_models:
            ba.clean()

        self.bank_account_models = BankAccountModel.objects.bulk_create(bank_account_models, ignore_conflicts=True)

    def create_uom_models(self):
        UOMs = {
            'unit': 'Unit',
            'ln.ft': 'Linear Feet',
            'sq.ft': 'Square Feet',
            'lb': 'Pound',
            'pallet': 'Pallet',
            'man-hour': 'Man Hour'
        }

        uom_models = [
            UnitOfMeasureModel(unit_abbr=abbr,
                               entity=self.entity_model,
                               name=name) for abbr, name in UOMs.items()
        ]
        self.uom_models = UnitOfMeasureModel.objects.bulk_create(uom_models)

    def create_products(self):
        product_count = randint(self.PRODUCTS_MIN, self.PRODUCTS_MAX)
        product_models = list()
        for i in range(product_count):
            is_inventory = random() > 0.75
            if is_inventory:
                product_models.append(ItemModel.add_root(
                    name=f'Product or Service {randint(1000, 9999)}',
                    uom=choice(self.uom_models),
                    item_type=choice(ItemModel.ITEM_CHOICES)[0],
                    sku=generate_random_sku(),
                    upc=generate_random_upc(),
                    item_id=generate_random_item_id(),
                    entity=self.entity_model,
                    for_inventory=is_inventory,
                    is_product_or_service=True,
                    earnings_account=choice(self.accounts_by_role[INCOME_OPERATIONAL]),
                    cogs_account=choice(self.accounts_by_role[COGS]),
                    inventory_account=choice(self.accounts_by_role[ASSET_CA_INVENTORY]),
                    additional_info=dict()
                ))
            else:
                product_models.append(ItemModel.add_root(
                    name=f'Product or Service {randint(1000, 9999)}',
                    uom=choice(self.uom_models),
                    item_type=choice(ItemModel.ITEM_CHOICES)[0],
                    sku=generate_random_sku(),
                    upc=generate_random_upc(),
                    item_id=generate_random_item_id(),
                    entity=self.entity_model,
                    for_inventory=is_inventory,
                    is_product_or_service=True,
                    earnings_account=choice(self.accounts_by_role[INCOME_OPERATIONAL]),
                    additional_info=dict()
                ))

        self.update_products()

    def update_products(self):
        self.product_and_services_models = ItemModel.objects.products_and_services(
            entity_slug=self.entity_model.slug,
            user_model=self.user_model
        )

    def update_inventory(self):
        self.inventory_models = ItemModel.objects.inventory(
            entity_slug=self.entity_model.slug,
            user_model=self.user_model
        )

    def update_expenses(self):
        self.expense_models = ItemModel.objects.expenses(
            entity_slug=self.entity_model.slug,
            user_model=self.user_model
        )

    def create_expenses(self):
        expense_count = randint(self.PRODUCTS_MIN, self.PRODUCTS_MAX)
        expense_models = [
            ItemModel.add_root(
                name=f'Expense Item {randint(1000, 9999)}',
                uom=choice(self.uom_models),
                item_type=choice(ItemModel.ITEM_CHOICES)[0],
                sku=generate_random_sku(),
                upc=generate_random_upc(),
                item_id=generate_random_item_id(),
                entity=self.entity_model,
                is_product_or_service=False,
                for_inventory=False,
                expense_account=choice(self.accounts_by_role[EXPENSE_REGULAR]),
            ) for _ in range(expense_count)
        ]

        self.update_expenses()

    def create_inventories(self):
        inv_count = randint(self.PRODUCTS_MIN, self.PRODUCTS_MAX)
        inventory_models = [
            ItemModel.add_root(
                name=f'Inventory {randint(1000, 9999)}',
                uom=choice(self.uom_models),
                item_type=choice(ItemModel.ITEM_CHOICES)[0],
                item_id=generate_random_item_id(),
                entity=self.entity_model,
                for_inventory=True,
                is_product_or_service=True if random() > 0.6 else False,
                earnings_account=choice(self.accounts_by_role[INCOME_OPERATIONAL]),
                cogs_account=choice(self.accounts_by_role[COGS]),
                inventory_account=choice(self.accounts_by_role[ASSET_CA_INVENTORY]),
            ) for _ in range(inv_count)
        ]

        self.update_inventory()

    def create_estimates(self, date_draft: date):
        customer_estimate: EstimateModel = EstimateModel(
            terms=choice(EstimateModel.CONTRACT_TERMS)[0],
            title=f'Customer Estimate {date_draft}',
            date_draft=date_draft
        )
        customer_estimate.configure(entity_slug=self.entity_model,
                                    user_model=self.user_model,
                                    customer_model=choice(self.customer_models))

        customer_estimate.save()

        estimate_items = [
            ItemTransactionModel(
                ce_model=customer_estimate,
                item_model=choice(self.product_and_services_models),
                ce_quantity=round(random() * randint(5, 15), 2),
                ce_unit_cost_estimate=round(random() * randint(50, 100), 2),
                ce_unit_revenue_estimate=round(random() * randint(80, 120) * (1 + 0.2 * random()), 2),
                entity_unit=choice(self.entity_unit_models) if random() > .75 else None
            ) for _ in range(randint(1, 10))
        ]

        for i in estimate_items:
            i.full_clean()

        customer_estimate.full_clean()
        customer_estimate.update_state(queryset=estimate_items)
        customer_estimate.save()

        estimate_items = customer_estimate.itemtransactionmodel_set.bulk_create(objs=estimate_items)

        if random() > 0.25:
            date_in_review = self.get_next_date(date_draft)
            customer_estimate.mark_as_review(commit=True, date_in_review=date_in_review)
            if random() > 0.50:
                date_approved = self.get_next_date(date_in_review)
                customer_estimate.mark_as_approved(commit=True, date_approved=date_approved)
                if random() > 0.25:
                    date_completed = self.get_next_date(date_approved)
                    customer_estimate.mark_as_completed(commit=True, date_completed=date_completed)
                elif random() > 0.8:
                    date_void = self.get_next_date(date_approved)
                    customer_estimate.mark_as_void(commit=True, date_void=date_void)
            elif random() > 0.8:
                date_canceled = self.get_next_date(date_in_review)
                customer_estimate.mark_as_canceled(commit=True, date_canceled=date_canceled)

    def create_bill(self, date_draft):

        bill_model: BillModel = BillModel(
            vendor=choice(self.vendor_models),
            accrue=random() > 0.65,
            progress=Decimal(str(round(random(), 2))),
            terms=choice(BillModel.TERMS)[0],
            amount_due=0,
            cash_account=choice(self.accounts_by_role[ASSET_CA_CASH]),
            prepaid_account=choice(self.accounts_by_role[ASSET_CA_PREPAID]),
            unearned_account=choice(self.accounts_by_role[LIABILITY_CL_ACC_PAYABLE]),
            date_draft=date_draft,
            additional_info=dict()
        )

        ledger_model, bill_model = bill_model.configure(
            entity_slug=self.entity_model,
            user_model=self.user_model)

        bill_model.full_clean()
        bill_model.save()

        bill_items = [
            ItemTransactionModel(
                bill_model=bill_model,
                item_model=choice(self.expense_models),
                quantity=round(random() * randint(5, 15), 2),
                unit_cost=round(random() * randint(50, 100), 2),
                entity_unit=choice(self.entity_unit_models) if random() > .75 else None
            ) for _ in range(randint(1, 10))
        ]

        for bi in bill_items:
            bi.full_clean()

        bill_model.update_amount_due(itemtxs_list=bill_items)
        bill_model.itemtransactionmodel_set.bulk_create(bill_items)
        bill_model.full_clean()
        bill_model.save()

        if random() > 0.25:
            date_in_review = self.get_next_date(date_draft)
            bill_model.mark_as_review(commit=True, date_in_review=date_in_review)

            if random() > 0.50:
                approved_date = self.get_next_date(date_in_review)
                bill_model.mark_as_approved(commit=True,
                                            entity_slug=self.entity_model.slug,
                                            user_model=self.user_model,
                                            approved_date=approved_date)

                if random() > 0.25:
                    paid_date = self.get_next_date(approved_date)
                    bill_model.mark_as_paid(
                        user_model=self.user_model,
                        entity_slug=self.entity_model.slug,
                        date_paid=paid_date,
                        commit=True
                    )
                elif random() > 0.8:
                    void_date = self.get_next_date(approved_date)
                    bill_model.mark_as_void(
                        user_model=self.user_model,
                        entity_slug=self.entity_model.slug,
                        void_date=void_date,
                        commit=True
                    )
            elif random() > 0.8:
                canceled_date = self.get_next_date(date_in_review)
                bill_model.mark_as_canceled(canceled_date=canceled_date)

    def create_po(self, date_draft: date):

        po_model: PurchaseOrderModel = PurchaseOrderModel(date_draft=date_draft)
        po_model = po_model.configure(entity_slug=self.entity_model, user_model=self.user_model)
        po_model.po_title = f'PO Title for {po_model.po_number}'
        po_model.save()

        po_items = [
            ItemTransactionModel(
                po_model=po_model,
                item_model=choice(self.inventory_models),
                po_quantity=round(random() * randint(3, 10), 2),
                po_unit_cost=round(random() * randint(100, 800), 2),
                entity_unit=choice(self.entity_unit_models) if random() > .75 else None
            ) for _ in range(randint(1, 10))
        ]

        for poi in po_items:
            poi.full_clean()

        po_model.update_state(itemtxs_list=po_items)
        po_model.full_clean()
        po_model.save()

        # pylint: disable=no-member
        po_items = po_model.itemtransactionmodel_set.bulk_create(po_items)

        # mark as approved...
        if random() > 0.25:
            date_review = self.get_next_date(date_draft)
            po_model.mark_as_review(commit=True, date_review=date_review)
            if random() > 0.5:
                date_approved = self.get_next_date(date_review)
                po_model.mark_as_approved(commit=True, date_approved=date_approved)
                if random() > 0.25:
                    # add a PO bill...
                    date_fulfilled = self.get_next_date(date_approved)
                    date_bill_draft = date_fulfilled - timedelta(days=randint(1, 3))

                    bill_model: BillModel = BillModel(
                        date_draft=date_bill_draft,
                        vendor=choice(self.vendor_models))

                    bill_model.cash_account = choice(self.accounts_by_role[ASSET_CA_CASH])
                    bill_model.prepaid_account = choice(self.accounts_by_role[ASSET_CA_PREPAID])
                    bill_model.unearned_account = choice(self.accounts_by_role[LIABILITY_CL_ACC_PAYABLE])

                    ledger_model, bill_model = bill_model.configure(
                        entity_slug=self.entity_model.slug,
                        user_model=self.user_model
                    )

                    bill_model.terms = choice([
                        BillModel.TERMS_ON_RECEIPT,
                        BillModel.TERMS_NET_30,
                        BillModel.TERMS_NET_60,
                        BillModel.TERMS_NET_90
                    ])

                    bill_model.full_clean()
                    bill_model.save()

                    for po_i in po_items:
                        po_i.po_total_amount = round(po_i.po_total_amount, 2)
                        po_i.total_amount = round(po_i.po_total_amount, 2)
                        po_i.quantity = round(po_i.po_quantity, 2)
                        po_i.unit_cost = round(po_i.po_unit_cost, 2)
                        po_i.bill_model = bill_model
                        po_i.po_item_status = ItemTransactionModel.STATUS_RECEIVED
                        po_i.full_clean()

                    bill_model.update_amount_due(itemtxs_list=po_items)
                    bill_model.full_clean()
                    bill_model.update_state()
                    bill_model.save()

                    po_model.itemtransactionmodel_set.bulk_update(
                        po_items,
                        fields=[
                            'po_total_amount',
                            'total_amount',
                            'po_quantity',
                            'quantity',
                            'po_unit_cost',
                            'unit_cost',
                            'bill_model',
                            'po_item_status'
                        ])

                    if random() > 0.25:
                        date_bill_review = self.get_next_date(date_bill_draft)
                        bill_model.mark_as_review(commit=True, date_in_review=date_bill_review)
                        if random() > 0.50:
                            bill_approve_date = self.get_next_date(date_bill_review)
                            bill_model.mark_as_approved(commit=True,
                                                        entity_slug=self.entity_model.slug,
                                                        user_model=self.user_model,
                                                        approved_date=bill_approve_date)
                            if random() > 0.25:
                                bill_paid_date = self.get_next_date(bill_approve_date)
                                bill_model.mark_as_paid(
                                    user_model=self.user_model,
                                    entity_slug=self.entity_model.slug,
                                    commit=True,
                                    date_paid=bill_paid_date)

                                if random() > 0.20:
                                    for po_i in po_items:
                                        po_i.po_item_status = ItemTransactionModel.STATUS_RECEIVED
                                        po_i.full_clean()

                                    # todo: can pass po items??..
                                    po_model.itemtransactionmodel_set.bulk_update(po_items,
                                                                                  fields=[
                                                                                      'po_item_status',
                                                                                      'updated'
                                                                                  ])
                                    po_model.mark_as_fulfilled(
                                        date_fulfilled=date_fulfilled,
                                        commit=True)
                                    self.entity_model.update_inventory(
                                        user_model=self.user_model,
                                        commit=True)
                                    self.update_products()
                                    self.update_inventory()

    def create_invoice(self, date_draft: date):

        invoice_model = InvoiceModel(
            customer=choice(self.customer_models),
            accrue=random() > 0.75,
            progress=Decimal(str(round(random(), 2))),
            terms=choice(InvoiceModel.TERMS)[0],
            cash_account=choice(self.accounts_by_role[ASSET_CA_CASH]),
            prepaid_account=choice(self.accounts_by_role[ASSET_CA_RECEIVABLES]),
            unearned_account=choice(self.accounts_by_role[LIABILITY_CL_DEFERRED_REVENUE]),
            date_draft=date_draft,
            additional_info=dict()
        )

        ledger_model, invoice_model = invoice_model.configure(
            entity_slug=self.entity_model,
            user_model=self.user_model)

        invoice_model.full_clean()
        invoice_model.save()

        invoice_items = list()

        for i in range(randint(1, 10)):
            item_model: ItemModel = choice(self.product_and_services_models)
            quantity = Decimal.from_float(round(random() * randint(1, 5), 2))
            entity_unit = choice(self.entity_unit_models) if random() > .75 else None
            margin = Decimal(random() + 1.5)
            avg_cost = item_model.get_average_cost()
            unit_cost = round(random() * randint(100, 999), 2)

            if item_model.for_inventory and item_model.is_product_or_service:
                if item_model.inventory_received is not None and item_model.inventory_received > 0.0:
                    if quantity > item_model.inventory_received:
                        quantity = item_model.inventory_received

                    # reducing inventory qty...
                    item_model.inventory_received -= quantity
                    item_model.inventory_received_value -= avg_cost * quantity
                    unit_cost = avg_cost * margin
                else:
                    quantity = 0.0
                    unit_cost = 0.0

            itm = ItemTransactionModel(
                invoice_model=invoice_model,
                item_model=item_model,
                quantity=quantity,
                unit_cost=unit_cost,
                entity_unit=entity_unit
            )
            itm.full_clean()
            invoice_items.append(itm)

        invoice_items = invoice_model.itemtransactionmodel_set.bulk_create(invoice_items)
        invoice_model.update_amount_due(itemtxs_list=invoice_items)
        invoice_model.full_clean()
        invoice_model.save()

        if random() > 0.25:
            date_review = self.get_next_date(date_draft)
            invoice_model.mark_as_review(commit=True, date_in_review=date_review)
            if random() > 0.50:
                date_approved = self.get_next_date(date_review)
                invoice_model.mark_as_approved(entity_slug=self.entity_model.slug,
                                               user_model=self.user_model,
                                               commit=True,
                                               approved_date=date_approved)
                if random() > 0.25:
                    date_paid = self.get_next_date(date_approved)
                    invoice_model.mark_as_paid(
                        entity_slug=self.entity_model.slug,
                        user_model=self.user_model,
                        date_paid=date_paid,
                        commit=True
                    )
                    self.entity_model.update_inventory(
                        user_model=self.user_model,
                        commit=True
                    )
                    self.update_inventory()
                    self.update_products()
                elif random() > 0.8:
                    date_void = self.get_next_date(date_approved)
                    invoice_model.mark_as_void(
                        entity_slug=self.entity_model.slug,
                        user_model=self.user_model,
                        date_void=date_void,
                        commit=True
                    )
            elif random() > 0.8:
                date_canceled = self.get_next_date(date_review)
                invoice_model.mark_as_canceled(commit=True, date_canceled=date_canceled)

    def fund_entity(self):

        capital_acc = choice(self.accounts_by_role[EQUITY_CAPITAL])
        cash_acc = choice(self.bank_account_models).cash_account

        ledger_model: LedgerModel = self.entity_model.add_equity(
            user_model=self.user_model,
            amount=self.capital_contribution,
            cash_account=cash_acc,
            equity_account=capital_acc,
            txs_date=self.start_date,
            ledger_name='Entity Funding for Sample Data',
            ledger_posted=True,
            je_posted=True
        )

    def recount_inventory(self):
        self.entity_model.update_inventory(
            user_model=self.user_model,
            commit=True
        )
