"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import date, timedelta
from decimal import Decimal
from itertools import groupby
from random import randint, random, choice
from typing import Union

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.timezone import localtime, localdate

from django_ledger.io import INCOME_SALES, ASSET_CA_INVENTORY, COGS, ASSET_CA_CASH, ASSET_CA_PREPAID, \
    LIABILITY_CL_DEFERRED_REVENUE
from django_ledger.models import EntityModel, TransactionModel, AccountModel, VendorModel, CustomerModel, \
    EntityUnitModel, BankAccountModel, LedgerModel, UnitOfMeasureModel, ItemModel, \
    BillModel, generate_bill_number, ItemThroughModel, PurchaseOrderModel, InvoiceModel, generate_invoice_number, \
    create_entity_unit_slug, EstimateModel, generate_estimate_number
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
        self.product_models = None
        self.expense_models = None
        self.inventory_models = None

        self.account_models = None
        self.accounts_by_role = None

        self.COUNTRY = 'US'
        self.NB_UNITS: int = 4

        self.PRODUCTS_MIN = 20
        self.PRODUCTS_MAX = 40

    def create_entity_units(self, nb_units: int = None):
        nb_units = self.NB_UNITS if not nb_units else nb_units

        if nb_units:
            assert nb_units >= 0, 'Number of unite must be greater than 0'

        self.entity_unit_models = [
            EntityUnitModel.objects.create(
                name=f'Unit {u}',
                slug=create_entity_unit_slug(
                    name=f'{self.entity_model.name}-Unit {u}'),
                entity=self.entity_model
            ) for u in range(nb_units)
        ]

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
                             cash_account=choice(self.accounts_by_role['asset_ca_cash']),
                             ledger=LedgerModel.objects.create(
                                 entity=self.entity_model,
                                 name=f'{self.entity_model.name} Checking Account',
                                 posted=True
                             )),
            BankAccountModel(name=f'{self.entity_model.name} Savings Account',
                             account_number=self.fk.bban(),
                             routing_number=self.fk.swift11(),
                             aba_number=self.fk.swift(),
                             account_type='savings',
                             cash_account=choice(self.accounts_by_role['asset_ca_cash']),
                             ledger=LedgerModel.objects.create(
                                 entity=self.entity_model,
                                 name=f'{self.entity_model.name} Savings Account',
                                 posted=True
                             ))
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
                product_models.append(ItemModel(
                    name=f'Product or Service {randint(1000, 9999)}',
                    uom=choice(self.uom_models),
                    item_type=choice(ItemModel.ITEM_CHOICES)[0],
                    sku=generate_random_sku(),
                    upc=generate_random_upc(),
                    item_id=generate_random_item_id(),
                    entity=self.entity_model,
                    for_inventory=is_inventory,
                    is_product_or_service=True,
                    earnings_account=choice(self.accounts_by_role[INCOME_SALES]),
                    cogs_account=choice(self.accounts_by_role[COGS]),
                    inventory_account=choice(self.accounts_by_role[ASSET_CA_INVENTORY])
                ))
            else:
                product_models.append(ItemModel(
                    name=f'Product or Service {randint(1000, 9999)}',
                    uom=choice(self.uom_models),
                    item_type=choice(ItemModel.ITEM_CHOICES)[0],
                    sku=generate_random_sku(),
                    upc=generate_random_upc(),
                    item_id=generate_random_item_id(),
                    entity=self.entity_model,
                    for_inventory=is_inventory,
                    is_product_or_service=True,
                    earnings_account=choice(self.accounts_by_role[INCOME_SALES]),
                ))

        for im in product_models:
            im.clean()

        self.product_models = self.entity_model.items.bulk_create(product_models, ignore_conflicts=True)

    def update_products(self):
        self.product_models = ItemModel.objects.products_and_services(
            entity_slug=self.entity_model.slug,
            user_model=self.user_model
        )

    def create_expenses(self):
        expense_count = randint(self.PRODUCTS_MIN, self.PRODUCTS_MAX)
        expense_models = [
            ItemModel(
                name=f'Expense Item {randint(1000, 9999)}',
                uom=choice(self.uom_models),
                item_type=choice(ItemModel.ITEM_CHOICES)[0],
                sku=generate_random_sku(),
                upc=generate_random_upc(),
                item_id=generate_random_item_id(),
                entity=self.entity_model,
                is_product_or_service=False,
                for_inventory=False,
                expense_account=choice(self.accounts_by_role['ex_op']),
            ) for _ in range(expense_count)
        ]

        for em in expense_models:
            em.clean()

        self.expense_models = self.entity_model.items.bulk_create(expense_models)

    def create_inventories(self):
        inv_count = randint(self.PRODUCTS_MIN, self.PRODUCTS_MAX)
        inventory_models = [
            ItemModel(
                name=f'Inventory {randint(1000, 9999)}',
                uom=choice(self.uom_models),
                item_type=choice(ItemModel.ITEM_CHOICES)[0],
                item_id=generate_random_item_id(),
                entity=self.entity_model,
                for_inventory=True,
                is_product_or_service=True if random() > 0.6 else False,
                earnings_account=choice(self.accounts_by_role[INCOME_SALES]),
                cogs_account=choice(self.accounts_by_role[COGS]),
                inventory_account=choice(self.accounts_by_role[ASSET_CA_INVENTORY]),
            ) for _ in range(inv_count)
        ]

        for i in inventory_models:
            i.clean()

        self.inventory_models = self.entity_model.items.bulk_create(inventory_models)

    def create_estimates(self, date_approved: date):
        estimate_number = generate_estimate_number()
        customer_estimate: EstimateModel = EstimateModel(
            estimate_number=estimate_number,
            terms=choice(EstimateModel.CONTRACT_TERMS)[0],
            title=f'Customer Estimate {estimate_number}',
        )
        customer_estimate.configure(entity_slug=self.entity_model,
                                    user_model=self.user_model,
                                    customer_model=choice(self.customer_models))

        estimate_items = [
            ItemThroughModel(
                ce_model=customer_estimate,
                item_model=choice(self.product_models),
                quantity=round(random() * randint(5, 15), 2),
                unit_cost=round(random() * randint(50, 100), 2),
                ce_unit_revenue_estimate=round(random() * randint(80, 120) * (1 + 0.2 * random()), 2),
                entity_unit=choice(self.entity_unit_models) if random() > .75 else None
            ) for _ in range(randint(1, 10))
        ]

        for i in estimate_items:
            i.clean()

        customer_estimate.full_clean()
        customer_estimate.save()
        customer_estimate.update_state(queryset=estimate_items)

        estimate_items = customer_estimate.itemthroughmodel_set.bulk_create(objs=estimate_items)

        if random() < 0.2:
            customer_estimate.mark_as_review(commit=True)
            if random() < 0.55:
                customer_estimate.mark_as_approved(commit=True, date_approved=date_approved)
                if random() < 0.80:
                    date_completed = date_approved + timedelta(days=randint(10, 45))
                    customer_estimate.mark_as_completed(commit=True, date_completed=date_completed)
            else:
                customer_estimate.mark_as_canceled(commit=True, date_canceled=date_approved)

    def create_bill(self,
                    is_accruable: bool,
                    progress: float,
                    issue_dt: date,
                    is_paid: bool,
                    paid_dt: date):

        bill_model: BillModel = BillModel(
            vendor=choice(self.vendor_models),
            accrue=is_accruable,
            progress=progress,
            terms=choice(BillModel.TERMS)[0],
            bill_number=generate_bill_number(),
            amount_due=0,
            cash_account=choice(self.accounts_by_role[ASSET_CA_CASH]),
            prepaid_account=choice(self.accounts_by_role[ASSET_CA_PREPAID]),
            unearned_account=choice(self.accounts_by_role[LIABILITY_CL_DEFERRED_REVENUE]),
            date=issue_dt,
            paid_date=paid_dt,
            additional_info=dict()
        )

        ledger_model, bill_model = bill_model.configure(
            entity_slug=self.entity_model,
            user_model=self.user_model,
            ledger_posted=True)

        bill_model.full_clean()
        bill_model.save()

        bill_items = [
            ItemThroughModel(
                bill_model=bill_model,
                item_model=choice(self.expense_models),
                quantity=round(random() * randint(5, 15), 2),
                unit_cost=round(random() * randint(50, 100), 2),
                entity_unit=choice(self.entity_unit_models) if random() > .75 else None
            ) for _ in range(randint(1, 10))
        ]

        for bi in bill_items:
            bi.full_clean()

        bill_model.update_amount_due(item_list=bill_items)
        bill_model.itemthroughmodel_set.bulk_create(bill_items)
        bill_model.full_clean()
        bill_model.save()

        if random() > 0.15:
            # bill_model.bill_status = BillModel.BILL_STATUS_APPROVED
            bill_model.mark_as_review(commit=True)

            if random() > 0.35:
                bill_model.mark_as_approved(commit=True)

                # todo: needs new method for bill payment???...
                bill_model.amount_paid = Decimal.from_float(round(random() * float(bill_model.amount_due), 2))
                bill_model.new_state(commit=True)
                bill_model.clean()
                bill_model.save()

                # pylint: disable=no-member
                bill_model.migrate_state(
                    user_model=self.user_model,
                    entity_slug=self.entity_model.slug,
                    je_date=issue_dt)

                if random() > 0.40:
                    bill_model.mark_as_paid(
                        user_model=self.user_model,
                        entity_slug=self.entity_model.slug,
                        commit=True
                    )
                    if random() > .90:
                        bill_model.mark_as_void(
                            user_model=self.user_model,
                            entity_slug=self.entity_model.slug,
                            commit=True
                        )

    def create_po(self, po_date: date):

        po_model: PurchaseOrderModel = PurchaseOrderModel(po_date=po_date)
        po_model = po_model.configure(
            entity_slug=self.entity_model,
            user_model=self.user_model,
        )
        po_model.po_title = f'PO Title for {po_model.po_number}'
        po_model.save()

        po_items = [
            ItemThroughModel(
                po_model=po_model,
                item_model=choice(self.inventory_models),
                po_quantity=round(random() * randint(3, 10), 2),
                po_unit_cost=round(random() * randint(100, 800), 2),
                entity_unit=choice(self.entity_unit_models) if random() > .75 else None
            ) for _ in range(randint(1, 10))
        ]

        for poi in po_items:
            poi.full_clean()

        po_model.update_po_state(item_list=po_items)
        po_model.full_clean()
        po_model.save()

        # pylint: disable=no-member
        po_items = po_model.itemthroughmodel_set.bulk_create(po_items)

        # mark as approved...
        if random() > 0.15:
            po_model.mark_as_review(commit=True)
            if random() > 0.5:
                po_model.mark_as_approved(commit=True, po_date=po_date)
                if random() > 0.5:
                    # add a PO bill...
                    ldt = self.localtime.date()
                    fulfilled_dt = po_date + timedelta(days=randint(4, 10))
                    bill_dt = po_date + timedelta(days=randint(1, 3))

                    if bill_dt > ldt:
                        bill_dt = ldt

                    bill_model: BillModel = BillModel(
                        bill_number=generate_bill_number(),
                        date=bill_dt,
                        vendor=choice(self.vendor_models))

                    bill_model.cash_account = choice(self.accounts_by_role[ASSET_CA_CASH])
                    bill_model.prepaid_account = choice(self.accounts_by_role[ASSET_CA_PREPAID])
                    bill_model.unearned_account = choice(self.accounts_by_role[LIABILITY_CL_DEFERRED_REVENUE])

                    ledger_model, bill_model = bill_model.configure(
                        # ledger_posted=True,
                        entity_slug=self.entity_model.slug,
                        user_model=self.user_model
                    )

                    bill_model.terms = choice([
                        BillModel.TERMS_ON_RECEIPT,
                        BillModel.TERMS_NET_30,
                        BillModel.TERMS_NET_60,
                        BillModel.TERMS_NET_90
                    ])
                    bill_model.save()

                    for po_i in po_items:
                        po_i.po_total_amount = round(po_i.po_total_amount, 2)
                        po_i.total_amount = round(po_i.po_total_amount, 2)
                        po_i.quantity = round(po_i.po_quantity, 2)
                        po_i.unit_cost = round(po_i.po_unit_cost, 2)
                        po_i.bill_model = bill_model
                        po_i.po_item_status = ItemThroughModel.STATUS_RECEIVED
                        po_i.full_clean()

                    bill_model.update_amount_due(item_list=po_items)
                    bill_model.full_clean()
                    bill_model.update_state()
                    bill_model.save()

                    po_model.itemthroughmodel_set.bulk_update(
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

                    if random() > 0.15:
                        bill_model.mark_as_review(commit=True)
                        if random() > 0.20:
                            bill_model.mark_as_approved(commit=True)
                            if random() > 0.25:
                                paid_date = bill_dt + timedelta(days=1)
                                if paid_date > ldt:
                                    paid_date = ldt
                                bill_model.mark_as_paid(
                                    user_model=self.user_model,
                                    entity_slug=self.entity_model.slug,
                                    commit=True,
                                    paid_date=paid_date)
                                if random() > 0.20:
                                    for po_i in po_items:
                                        po_i.po_item_status = ItemThroughModel.STATUS_RECEIVED
                                        po_i.full_clean()
                                    po_model.itemthroughmodel_set.bulk_update(po_items,
                                                                              fields=[
                                                                                  'po_item_status',
                                                                                  'updated'
                                                                              ])
                                    po_model.mark_as_fulfilled(
                                        fulfilled_date=fulfilled_dt,
                                        # po_items=po_items,
                                        commit=True)

    def create_invoice(self,
                       is_accruable: bool,
                       progress: float,
                       issue_dt: date,
                       paid_dt: date):

        if not paid_dt:
            paid_dt = localdate()

        invoice_model = InvoiceModel(
            customer=choice(self.customer_models),
            accrue=is_accruable,
            progress=progress,
            terms=choice(InvoiceModel.TERMS)[0],
            invoice_number=generate_invoice_number(),
            cash_account=choice(self.accounts_by_role[ASSET_CA_CASH]),
            prepaid_account=choice(self.accounts_by_role[ASSET_CA_PREPAID]),
            unearned_account=choice(self.accounts_by_role[LIABILITY_CL_DEFERRED_REVENUE]),
            date=issue_dt,
            additional_info=dict()
        )

        ledger_model, invoice_model = invoice_model.configure(
            entity_slug=self.entity_model,
            user_model=self.user_model)

        invoice_model.full_clean()
        invoice_model.save()

        invoice_items = list()

        for i in range(randint(1, 10)):
            item_model: ItemModel = choice(self.product_models)
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

            itm = ItemThroughModel(
                invoice_model=invoice_model,
                item_model=item_model,
                quantity=quantity,
                unit_cost=unit_cost,
                entity_unit=entity_unit
            )
            itm.full_clean()
            invoice_items.append(itm)

        invoice_items = invoice_model.itemthroughmodel_set.bulk_create(invoice_items)
        invoice_model.update_amount_due(item_list=invoice_items)
        invoice_model.full_clean()
        invoice_model.save()

        if random() > 0.15:
            invoice_model.mark_as_review(commit=True)
            if random() > 0.15:
                invoice_model.mark_as_approved(commit=True)
                if random() > 0.3:
                    print(issue_dt, paid_dt)
                    invoice_model.mark_as_paid(
                        entity_slug=self.entity_model.slug,
                        user_model=self.user_model,
                        paid_date=paid_dt,
                        commit=True
                    )
                    if random() > 0.80:
                        invoice_model.mark_as_void(
                            entity_slug=self.entity_model.slug,
                            user_model=self.user_model,
                            void_date=paid_dt + timedelta(days=randint(1, 6)),
                            commit=True
                        )
            else:
                invoice_model.mark_as_canceled(commit=True)

    def fund_entity(self):

        capital_acc = choice(self.accounts_by_role['eq_capital'])
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

    def populate_entity(self):

        txs_qs = TransactionModel.objects.for_entity(
            entity_model=self.entity_model,
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

            issue_dttm = self.start_date + timedelta(days=randint(0, self.DAYS_FORWARD))
            if issue_dttm > self.localtime:
                issue_dttm = self.localtime

            is_accruable = random() < self.is_accruable_probability
            progress = Decimal(round(random(), 2)) if is_accruable else 0

            is_paid = random() < self.is_paid_probability
            paid_dttm = issue_dttm + timedelta(days=randint(0, 60)) if is_paid else None
            if paid_dttm and paid_dttm >= self.localtime:
                paid_dttm = None
                is_paid = False

            issue_dt = issue_dttm.date()
            paid_dt = paid_dttm.date() if paid_dttm else None

            self.create_estimates(date_approved=issue_dt)

            if i < self.tx_quantity / 2:
                self.create_bill(
                    is_accruable=is_accruable,
                    progress=progress,
                    issue_dt=issue_dt,
                    is_paid=is_paid,
                    paid_dt=paid_dt
                )

                if random() > 0.4:
                    self.create_po(po_date=issue_dt)

            else:
                if count_inventory:
                    self.recount_inventory()
                    count_inventory = False
                    self.update_products()

                self.create_invoice(
                    is_accruable=is_accruable,
                    progress=progress,
                    issue_dt=issue_dt,
                    paid_dt=paid_dt
                )

            ItemModel.objects.bulk_update(self.product_models,
                                          fields=[
                                              'inventory_received',
                                              'inventory_received_value'
                                          ])
