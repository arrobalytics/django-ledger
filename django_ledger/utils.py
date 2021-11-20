from datetime import datetime, timedelta, date
from decimal import Decimal
from itertools import groupby
from random import choice, random, randint
from string import ascii_uppercase, ascii_lowercase, digits
from typing import Tuple

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.utils.timezone import localtime, localdate

from django_ledger.io.roles import (ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_DEFERRED_REVENUE,
                                    COGS, ASSET_CA_INVENTORY, INCOME_SALES)
from django_ledger.models import (AccruableItemMixIn, generate_po_number, PurchaseOrderModel, EntityModel,
                                  LedgerModel, BankAccountModel, AccountModel, VendorModel, CustomerModel,
                                  UnitOfMeasureModel, ItemModel, ItemThroughModel, TransactionModel)
from django_ledger.models import generate_invoice_number, InvoiceModel, generate_bill_number, BillModel
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.unit import create_entity_unit_slug, EntityUnitModel

UserModel = get_user_model()

FAKER_IMPORTED = False

SKU_UPC_CHARS = ascii_uppercase + digits
ITEM_ID_CHARS = ascii_uppercase + ascii_lowercase + digits


def generate_random_sku(length=12):
    return ''.join(choice(SKU_UPC_CHARS) for _ in range(length))


def generate_random_upc(length=10):
    return ''.join(choice(SKU_UPC_CHARS) for _ in range(length))


def generate_random_item_id(length=20):
    return ''.join(choice(ITEM_ID_CHARS) for _ in range(length))


def new_po_protocol(po_model: PurchaseOrderModel,
                    entity_slug: str or EntityModel,
                    user_model: UserModel,
                    po_date: date = None) -> PurchaseOrderModel:
    if isinstance(entity_slug, str):
        entity_qs = EntityModel.objects.for_user(
            user_model=user_model)
        entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
    elif isinstance(entity_slug, EntityModel):
        entity_model = entity_slug
    else:
        raise ValidationError('entity_slug must be an instance of str or EntityModel')

    po_model.po_number = generate_po_number()
    if po_date:
        po_model.po_date = po_date
    po_model.entity = entity_model
    return po_model


def new_bill_protocol(bill_model: BillModel,
                      entity_slug: str or EntityModel,
                      user_model: UserModel,
                      bill_desc: str = None) -> Tuple[LedgerModel, BillModel]:
    if isinstance(entity_slug, str):
        entity_qs = EntityModel.objects.for_user(
            user_model=user_model)
        entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
    elif isinstance(entity_slug, EntityModel):
        entity_model = entity_slug
    else:
        raise ValidationError('entity_slug must be an instance of str or EntityModel')

    bill_model.bill_number = generate_bill_number()
    ledger_name = f'Bill {bill_model.bill_number}'
    if bill_desc:
        ledger_name += f' | {bill_desc}'
    ledger_model: LedgerModel = LedgerModel.objects.create(
        entity=entity_model,
        posted=True,
        name=ledger_name,
    )
    ledger_model.clean()
    bill_model.ledger = ledger_model
    return ledger_model, bill_model


def new_invoice_protocol(invoice_model: InvoiceModel,
                         entity_slug: str or EntityModel,
                         user_model: UserModel) -> Tuple[LedgerModel, InvoiceModel]:
    if isinstance(entity_slug, str):
        entity_qs = EntityModel.objects.for_user(
            user_model=user_model)
        entity_model: EntityModel = get_object_or_404(entity_qs, slug__exact=entity_slug)
    elif isinstance(entity_slug, EntityModel):
        entity_model = entity_slug
    else:
        raise ValidationError('entity_slug must be an instance of str or EntityModel')

    if not invoice_model.invoice_number:
        invoice_model.invoice_number = generate_invoice_number()
    ledger_model = LedgerModel.objects.create(
        entity=entity_model,
        posted=True,
        name=f'Invoice {invoice_model.invoice_number}',
    )
    ledger_model.clean()
    invoice_model.ledger = ledger_model
    return ledger_model, invoice_model


def new_bankaccount_protocol(bank_account_model: BankAccountModel,
                             entity_slug: str or EntityModel,
                             user_model: UserModel,
                             posted_ledger: bool = True) -> BankAccountModel:
    if isinstance(entity_slug, str):
        entity_model = EntityModel.objects.for_user(
            user_model=user_model).get(
            slug__exact=entity_slug)
    elif isinstance(entity_slug, EntityModel):
        entity_model = entity_slug
    else:
        raise ValidationError('entity_slug must be an instance of str or EntityModel')

    ledger_model = LedgerModel.objects.create(
        entity=entity_model,
        posted=posted_ledger,
        name=f'Bank Account {"***" + bank_account_model.account_number[-4:]}'
    )
    ledger_model.clean()
    bank_account_model.ledger = ledger_model
    return bank_account_model


def populate_default_coa(entity_model: EntityModel, activate_accounts: bool = False):
    acc_objs = [AccountModel(
        code=a['code'],
        name=a['name'],
        role=a['role'],
        balance_type=a['balance_type'],
        active=activate_accounts,
        coa=entity_model.coa,
    ) for a in CHART_OF_ACCOUNTS]

    for acc in acc_objs:
        acc.full_clean()
        acc.save()


def make_accounts_active(entity_model: EntityModel, account_code_set: set):
    accounts = entity_model.coa.accounts.filter(code__in=account_code_set)
    accounts.update(active=True)


def get_end_date_session_key(entity_slug: str):
    return f'djl_end_date_filter_{entity_slug}'.replace('-', '_')


def get_default_entity_session_key():
    return 'djl_default_entity_model'


def get_default_unit_session_key():
    return 'djl_default_unit_model'


def set_default_entity(request, entity_model: EntityModel):
    session_key = get_default_entity_session_key()
    if not request.session.get(session_key):
        request.session[session_key] = {
            'entity_uuid': str(entity_model.uuid),
            'entity_slug': entity_model.slug,
            'entity_name': entity_model.name,
        }
    elif request.session[session_key].get('entity_slug') != entity_model.slug:
        request.session[session_key] = {
            'entity_uuid': str(entity_model.uuid),
            'entity_slug': entity_model.slug,
            'entity_name': entity_model.name,
        }


def get_default_entity_from_session(request):
    session_key = get_default_entity_session_key()
    return request.session.get(session_key)


def set_session_date_filter(request, entity_slug: str, end_date: date):
    session_key = get_end_date_session_key(entity_slug)
    request.session[session_key] = end_date.isoformat()


def create_random_vendors(entity_model: EntityModel, fk):
    vendor_count = randint(10, 20)
    vendor_models = [
        VendorModel(
            vendor_name=fk.name() if random() > .7 else fk.company(),
            entity=entity_model,
            address_1=fk.street_address(),
            address_2=fk.building_number() if random() < .2 else None,
            city=fk.city(),
            state=fk.state_abbr(),
            zip_code=fk.postcode(),
            phone=fk.phone_number(),
            country='USA',
            email=fk.email(),
            website=fk.url(),
            active=True,
            hidden=False
        ) for _ in range(vendor_count)
    ]

    for vendor in vendor_models:
        vendor.clean()

    return VendorModel.objects.bulk_create(vendor_models, ignore_conflicts=True)


def create_random_customers(entity_model: EntityModel, fk):
    customer_count = randint(10, 20)
    customer_models = [
        CustomerModel(
            customer_name=fk.name() if random() > .2 else fk.company(),
            entity=entity_model,
            address_1=fk.street_address() + fk.street_suffix(),
            address_2=fk.building_number() if random() > .2 else None,
            city=fk.city(),
            state=fk.state_abbr(),
            zip_code=fk.postcode(),
            country='USA',
            phone=fk.phone_number(),
            email=fk.email(),
            website=fk.url(),
            active=True,
            hidden=False
        ) for _ in range(customer_count)
    ]

    for customer in customer_models:
        customer.clean()

    return CustomerModel.objects.bulk_create(customer_models, ignore_conflicts=True)


def fund_entity(entity_model: EntityModel,
                bank_accounts: QuerySet,
                start_dt: date,
                accounts_gb: dict,
                cap_contribution: float or int):
    capital_acc = choice(accounts_gb['eq_capital'])
    cash_acc = choice(bank_accounts).cash_account

    txs = list()
    txs.append({
        'account_id': cash_acc.uuid,
        'tx_type': 'debit',
        'amount': cap_contribution,
        'description': f'Sample data for {entity_model.name}'
    })
    txs.append({
        'account_id': capital_acc.uuid,
        'tx_type': 'credit',
        'amount': cap_contribution,
        'description': f'Sample data for {entity_model.name}'
    })

    ledger, created = entity_model.ledgermodel_set.get_or_create(
        name='Business Funding Ledger',
        posted=True
    )
    entity_model.commit_txs(
        je_date=start_dt,
        je_txs=txs,
        je_activity='op',
        je_posted=True,
        je_ledger=ledger
    )


def create_uom_models(entity_model: EntityModel):
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
                           entity=entity_model,
                           name=name) for abbr, name in UOMs.items()
    ]
    return UnitOfMeasureModel.objects.bulk_create(uom_models)


def generate_random_products(entity_model: EntityModel,
                             uom_models,
                             accounts_gb,
                             min_products: int = 20,
                             max_products: int = 40):
    product_count = randint(min_products, max_products)
    product_models = [
        ItemModel(
            name=f'Product or Service {randint(1000, 9999)}',
            uom=choice(uom_models),
            sku=generate_random_sku(),
            upc=generate_random_upc(),
            item_id=generate_random_item_id(),
            entity=entity_model,
            for_inventory=False,
            is_product_or_service=True,
            earnings_account=choice(accounts_gb[INCOME_SALES]),
        ) for _ in range(product_count)
    ]

    for im in product_models:
        im.clean()

    product_models = entity_model.items.bulk_create(product_models)
    return product_models


def generate_random_inventories(entity_model: EntityModel,
                                uom_models,
                                accounts_gb,
                                min_inventory: int = 20,
                                max_inventory: int = 40):
    inv_count = randint(min_inventory, max_inventory)
    inventory_models = [
        ItemModel(
            name=f'Inventory {randint(1000, 9999)}',
            uom=choice(uom_models),
            item_id=generate_random_item_id(),
            entity=entity_model,
            for_inventory=True,
            is_product_or_service=True if random() > 0.6 else False,
            earnings_account=choice(accounts_gb[INCOME_SALES]),
            cogs_account=choice(accounts_gb[COGS]),
            inventory_account=choice(accounts_gb[ASSET_CA_INVENTORY]),
        ) for _ in range(inv_count)
    ]

    for i in inventory_models:
        i.clean()

    inventory_models = entity_model.items.bulk_create(inventory_models)
    return inventory_models


def generate_random_expenses(entity_model: EntityModel,
                             uom_models,
                             accounts_gb,
                             min_expenses: int = 20,
                             max_expenses: int = 40):
    expense_count = randint(min_expenses, max_expenses)
    expense_models = [
        ItemModel(
            name=f'Expense Item {randint(1000, 9999)}',
            uom=choice(uom_models),
            sku=generate_random_sku(),
            upc=generate_random_upc(),
            item_id=generate_random_item_id(),
            entity=entity_model,
            is_product_or_service=False,
            for_inventory=False,
            expense_account=choice(accounts_gb['ex_op']),
        ) for _ in range(expense_count)
    ]

    for em in expense_models:
        em.clean()

    expense_models = entity_model.items.bulk_create(expense_models)

    return expense_models


def generate_random_invoice(
        entity_model: EntityModel,
        unit_models: list,
        customer_models,
        user_model,
        is_accruable: bool,
        progress: float,
        accounts_by_role: dict,
        issue_dt: date,
        is_paid: bool,
        paid_dt: date,
        product_models):
    invoice_model = InvoiceModel(
        customer=choice(customer_models),
        accrue=is_accruable,
        progress=progress,
        terms=choice(InvoiceModel.TERMS)[0],
        invoice_number=generate_invoice_number(),
        amount_due=0,
        cash_account=choice(accounts_by_role[ASSET_CA_CASH]),
        prepaid_account=choice(accounts_by_role[ASSET_CA_PREPAID]),
        unearned_account=choice(accounts_by_role[LIABILITY_CL_DEFERRED_REVENUE]),
        date=issue_dt,
        paid=is_paid,
        paid_date=paid_dt
    )

    ledger_model, invoice_model = new_invoice_protocol(
        invoice_model=invoice_model,
        entity_slug=entity_model,
        user_model=user_model)

    invoice_items = list()

    for i in range(randint(1, 10)):
        item_model: ItemModel = choice(product_models)
        quantity = Decimal.from_float(round(random() * randint(1, 5), 2))
        entity_unit = choice(unit_models) if random() > .75 else None
        margin = Decimal(random() * 0.5 + 1)
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
        itm.clean()
        invoice_items.append(itm)

    invoice_model.update_amount_due(item_list=invoice_items)
    invoice_model.amount_paid = Decimal.from_float(round(random() * float(invoice_model.amount_due), 2))
    invoice_model.new_state(commit=True)
    invoice_model.clean()
    invoice_model.save()
    invoice_model.itemthroughmodel_set.bulk_create(invoice_items)
    invoice_model.migrate_state(
        user_model=user_model,
        entity_slug=entity_model.slug,
        je_date=issue_dt)

    if is_paid:
        ledger_model.locked = True
        ledger_model.save(update_fields=['locked'])


def generate_random_bill(
        entity_model: EntityModel,
        unit_models: list,
        user_model,
        vendor_models: list,
        expense_models: list,
        is_accruable: bool,
        progress: float,
        accounts_by_role: dict,
        issue_dt: date,
        is_paid: bool,
        paid_dt: date):
    bill_model: BillModel = BillModel(
        vendor=choice(vendor_models),
        accrue=is_accruable,
        progress=progress,
        terms=choice(BillModel.TERMS)[0],
        bill_number=generate_bill_number(),
        amount_due=0,
        cash_account=choice(accounts_by_role[ASSET_CA_CASH]),
        prepaid_account=choice(accounts_by_role[ASSET_CA_PREPAID]),
        unearned_account=choice(accounts_by_role[LIABILITY_CL_DEFERRED_REVENUE]),
        date=issue_dt,
        paid=is_paid,
        paid_date=paid_dt
    )

    ledger_model, bill_model = new_bill_protocol(
        bill_model=bill_model,
        entity_slug=entity_model,
        user_model=user_model)

    bill_items = [
        ItemThroughModel(
            bill_model=bill_model,
            item_model=choice(expense_models),
            quantity=round(random() * randint(1, 5), 2),
            unit_cost=round(random() * randint(100, 800), 2),
            entity_unit=choice(unit_models) if random() > .75 else None
        ) for _ in range(randint(1, 10))
    ]

    for bi in bill_items:
        bi.clean()

    bill_model.update_amount_due(item_list=bill_items)
    bill_model.amount_paid = Decimal.from_float(round(random() * float(bill_model.amount_due), 2))
    bill_model.new_state(commit=True)
    bill_model.clean()
    bill_model.save()
    bill_model.itemthroughmodel_set.bulk_create(bill_items)
    bill_model.migrate_state(
        user_model=user_model,
        entity_slug=entity_model.slug,
        je_date=issue_dt)

    if is_paid:
        ledger_model.locked = True
        ledger_model.save(update_fields=['locked'])


def create_bank_accounts(entity_model: EntityModel, fk, accounts_by_role):
    bank_account_models = [
        BankAccountModel(name=f'{entity_model.name} Checking Account',
                         account_number=fk.bban(),
                         routing_number=fk.swift11(),
                         aba_number=fk.swift(),
                         account_type='checking',
                         cash_account=choice(accounts_by_role['asset_ca_cash']),
                         ledger=LedgerModel.objects.create(
                             entity=entity_model,
                             name=f'{entity_model.name} Checking Account',
                             posted=True
                         )),
        BankAccountModel(name=f'{entity_model.name} Savings Account',
                         account_number=fk.bban(),
                         routing_number=fk.swift11(),
                         aba_number=fk.swift(),
                         account_type='savings',
                         cash_account=choice(accounts_by_role['asset_ca_cash']),
                         ledger=LedgerModel.objects.create(
                             entity=entity_model,
                             name=f'{entity_model.name} Savings Account',
                             posted=True
                         )),
    ]
    for ba in bank_account_models:
        ba.clean()
    return BankAccountModel.objects.bulk_create(bank_account_models)


def create_random_entity_unit_models(entity_model, nb_units: int = 4):
    return [
        EntityUnitModel.objects.create(
            name=f'Unit {u}',
            slug=create_entity_unit_slug(f'{entity_model.name}-Unit {u}'),
            entity=entity_model
        ) for u in range(nb_units)
    ]


def generate_random_po(
        entity_model: EntityModel,
        unit_models: list,
        user_model,
        po_date: date,
        po_item_models,
        vendor_models,
        accounts_by_role):
    po_model: PurchaseOrderModel = PurchaseOrderModel()
    po_model = new_po_protocol(
        po_model=po_model,
        entity_slug=entity_model,
        user_model=user_model,
        po_date=po_date
    )
    po_model.po_title = f'PO Title for {po_model.po_number}'

    po_items = [
        ItemThroughModel(
            po_model=po_model,
            item_model=choice(po_item_models),
            po_quantity=round(random() * randint(3, 10), 2),
            po_unit_cost=round(random() * randint(100, 800), 2),
            entity_unit=choice(unit_models) if random() > .75 else None
        ) for _ in range(randint(1, 10))
    ]

    for poi in po_items:
        poi.clean()

    po_model.update_po_state(item_list=po_items)

    po_model.clean()
    po_model.save()

    # pylint: disable=no-member
    po_items = po_model.itemthroughmodel_set.bulk_create(po_items)

    # mark as approved...
    if random() > 0.3:
        po_model.mark_as_approved(commit=True)

        # mark as fulfilled...
        if random() > 0.5:
            ldt = localdate()
            fulfilled_dt = po_date + timedelta(days=randint(4, 10))
            bill_dt = po_date + timedelta(days=randint(1, 3))

            if bill_dt > ldt:
                bill_dt = ldt

            bill_model: BillModel = BillModel(
                bill_number=f'Bill for {po_model.po_number}',
                date=bill_dt,
                vendor=choice(vendor_models))
            ledger_model, bill_model = new_bill_protocol(
                bill_model=bill_model,
                entity_slug=entity_model.slug,
                user_model=user_model
            )
            bill_model.amount_due = po_model.po_amount
            bill_model.paid = True

            paid_date = bill_dt + timedelta(days=1)
            if paid_date > ldt:
                paid_date = ldt
            bill_model.paid_date = paid_date

            bill_model.cash_account = choice(accounts_by_role[ASSET_CA_CASH])
            bill_model.prepaid_account = choice(accounts_by_role[ASSET_CA_PREPAID])
            bill_model.unearned_account = choice(accounts_by_role[LIABILITY_CL_DEFERRED_REVENUE])
            bill_model.terms = choice([
                BillModel.TERMS_ON_RECEIPT,
                BillModel.TERMS_NET_30,
                BillModel.TERMS_NET_60,
                BillModel.TERMS_NET_60,
                # BillModel.TERMS_NET_90_PLUS,
            ])
            bill_model.clean()
            bill_model.update_state()
            bill_model.save()
            for po_i in po_items:
                po_i.total_amount = po_i.po_total_amount
                po_i.quantity = po_i.po_quantity
                po_i.unit_cost = po_i.po_unit_cost
                po_i.bill_model = bill_model
                po_i.po_item_status = ItemThroughModel.STATUS_RECEIVED
                po_i.clean()
            ItemThroughModel.objects.bulk_update(
                po_items,
                fields=[
                    'po_total_amount',
                    'total_amount',
                    'po_quantity',
                    'quantity',
                    'po_unit_cost',
                    'unit_cost',
                    'bill_model',
                    'po_item_status'])
            bill_model.migrate_state(
                user_model=user_model,
                entity_slug=entity_model.slug,
                # itemthrough_queryset=po_items
            )

            po_model.mark_as_fulfilled(date=fulfilled_dt, commit=True, po_items=po_items)


def generate_sample_data(entity_model: str or EntityModel,
                         user_model,
                         start_dt: datetime,
                         days_fw: int,
                         cap_contribution: float or int = 20000,
                         tx_quantity: int = 25,
                         is_accruable_probability: float = 0.2,
                         is_paid_probability: float = 0.90):
    try:
        from faker import Faker
        from faker.providers import company, address, phone_number, bank

        global FAKER_IMPORTED
        FAKER_IMPORTED = True

        fk = Faker(['en_US'])
        fk.add_provider(company)
        fk.add_provider(address)
        fk.add_provider(phone_number)
        fk.add_provider(bank)

    except ImportError:
        return False

    if not isinstance(entity_model, EntityModel):
        entity_model: EntityModel = EntityModel.objects.get(slug__exact=entity_model)

    txs_qs = TransactionModel.objects.for_entity(
        user_model=user_model,
        entity_model=entity_model
    )

    if txs_qs.count() > 0:
        raise ValidationError(
            f'Cannot populate random data on {entity_model.name} because it already has existing Transactions')

    account_models = AccountModel.on_coa.for_entity_available(
        entity_slug=entity_model.slug,
        user_model=user_model
    ).order_by('role')

    accounts_by_role = {
        g: list(v) for g, v in groupby(account_models, key=lambda a: a.role)
    }

    vendor_models = create_random_vendors(entity_model, fk)
    customer_models = create_random_customers(entity_model, fk)
    unit_models = create_random_entity_unit_models(entity_model)
    bank_accounts = create_bank_accounts(entity_model, fk, accounts_by_role)

    fund_entity(entity_model=entity_model,
                bank_accounts=bank_accounts,
                start_dt=start_dt,
                accounts_gb=accounts_by_role,
                cap_contribution=cap_contribution)

    uom_models = create_uom_models(entity_model=entity_model)
    product_models = generate_random_products(entity_model=entity_model,
                                              uom_models=uom_models,
                                              accounts_gb=accounts_by_role)

    expense_models = generate_random_expenses(entity_model=entity_model,
                                              uom_models=uom_models,
                                              accounts_gb=accounts_by_role)

    inventory_models = generate_random_inventories(entity_model=entity_model,
                                                   uom_models=uom_models,
                                                   accounts_gb=accounts_by_role)

    loc_time = localtime()
    count_inventory = True

    for i in range(tx_quantity):

        issue_dttm = start_dt + timedelta(days=randint(0, days_fw))
        if issue_dttm > loc_time:
            issue_dttm = loc_time

        is_accruable = random() < is_accruable_probability
        progress = Decimal(round(random(), 2)) if is_accruable else 0

        is_paid = random() < is_paid_probability
        paid_dttm = issue_dttm + timedelta(days=randint(0, 60)) if is_paid else None
        if paid_dttm and paid_dttm >= loc_time:
            paid_dttm = None
            is_paid = False

        issue_dt = issue_dttm.date()
        paid_dt = paid_dttm.date() if paid_dttm else None

        # process the first half adding bills and POs...
        if i < tx_quantity / 2:
            generate_random_bill(
                entity_model=entity_model,
                unit_models=unit_models,
                vendor_models=vendor_models,
                is_accruable=is_accruable,
                progress=progress,
                accounts_by_role=accounts_by_role,
                issue_dt=issue_dt,
                is_paid=is_paid,
                paid_dt=paid_dt,
                user_model=user_model,
                expense_models=expense_models
            )

            if random() > .40:
                generate_random_po(
                    entity_model=entity_model,
                    unit_models=unit_models,
                    user_model=user_model,
                    po_date=issue_dt,
                    po_item_models=inventory_models,
                    vendor_models=vendor_models,
                    accounts_by_role=accounts_by_role
                )

        else:
            if count_inventory:
                entity_model.update_inventory(
                    user_model=user_model,
                    commit=True
                )
                count_inventory = False
                product_models = ItemModel.objects.products_and_services(
                    entity_slug=entity_model.slug,
                    user_model=user_model
                )

            generate_random_invoice(
                entity_model=entity_model,
                unit_models=unit_models,
                customer_models=customer_models,
                is_accruable=is_accruable,
                progress=progress,
                accounts_by_role=accounts_by_role,
                issue_dt=issue_dt,
                is_paid=is_paid,
                paid_dt=paid_dt,
                user_model=user_model,
                product_models=product_models
            )

        ItemModel.objects.bulk_update(product_models, fields=[
            'inventory_received',
            'inventory_received_value'
        ])


def accruable_net_summary(queryset: QuerySet) -> dict:
    """
    A convenience function that computes current net summary of accruable models.
    "net_30" group indicates the total amount is due in 30 days or less.
    "net_0" group indicates total past due amount.

    :param queryset: Accruable Objects Queryset.
    :return: A dictionary summarizing current net summary 0,30,60,90,90+ bill open amounts.
    """
    nets = {
        'net_0': 0,
        'net_30': 0,
        'net_60': 0,
        'net_90': 0,
        'net_90+': 0
    }
    nets_collect = [{
        'net_due_group': b.net_due_group(),
        'amount_open': b.get_amount_open()
    } for b in queryset]
    nets_collect.sort(key=lambda b: b['net_due_group'])
    nets_collect = {
        g: float(sum(b['amount_open'] for b in l)) for g, l in groupby(nets_collect, key=lambda b: b['net_due_group'])
    }
    nets.update(nets_collect)
    return nets


def mark_accruable_paid(accruable_model: AccruableItemMixIn, user_model, entity_slug: str):
    accruable_model.paid = True
    accruable_model.clean()
    accruable_model.save()
    accruable_model.migrate_state(
        user_model=user_model,
        entity_slug=entity_slug
    )

    ledger = accruable_model.ledger
    ledger.locked = True
    ledger.save(update_fields=['locked'])


def get_end_date_from_session(entity_slug: str, request) -> date:
    session_end_date_filter = get_end_date_session_key(entity_slug)
    end_date = request.session.get(session_end_date_filter)
    end_date = parse_date(end_date) if end_date else localdate()
    return end_date


def prepare_context_by_unit(context: dict):
    unit_model = context.get('unit_model')
    if unit_model:
        unit_slug = unit_model.slug
        by_unit = True
    else:
        unit_slug = context['view'].kwargs.get('unit_slug')
        if not unit_slug:
            unit_slug = context['request'].GET.get('unit_slug')
            try:
                by_unit = context['request'].GET.get('by_unit')
                by_unit = bool(int(by_unit))
            except ValueError:
                by_unit = False
            except TypeError:
                by_unit = False
            context['by_unit'] = by_unit
        else:
            by_unit = False
    context['unit_slug'] = unit_slug
    context['unit_model'] = unit_model
    context['by_unit'] = by_unit
