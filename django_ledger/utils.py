from datetime import datetime, timedelta, date
from decimal import Decimal
from itertools import groupby
from random import choice, random, randint
from string import ascii_uppercase, ascii_lowercase, digits

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.utils.dateparse import parse_date
from django.utils.timezone import localtime, localdate

from django_ledger.models.accounts import AccountModel
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.bill import BillModel, generate_bill_number, BillModelItemsThroughModel
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel, generate_invoice_number, InvoiceModelItemsThroughModel
from django_ledger.models.items import UnitOfMeasureModel, ItemModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.mixins import AccruableItemMixIn
from django_ledger.models.vendor import VendorModel

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


def new_bill_protocol(bill_model: BillModel, entity_slug: str or EntityModel, user_model: UserModel) -> BillModel:
    if isinstance(entity_slug, str):
        entity_model = EntityModel.objects.for_user(
            user_model=user_model).get(
            slug__exact=entity_slug)
    elif isinstance(entity_slug, EntityModel):
        entity_model = entity_slug
    else:
        raise ValidationError('entity_slug must be an instance of str or EntityModel')

    bill_model.bill_number = generate_bill_number()
    ledger_model = LedgerModel.objects.create(
        entity=entity_model,
        posted=True,
        name=f'Bill {bill_model.bill_number}'
    )
    ledger_model.clean()
    bill_model.ledger = ledger_model
    return bill_model


def new_invoice_protocol(invoice_model: InvoiceModel,
                         entity_slug: str or EntityModel,
                         user_model: UserModel) -> InvoiceModel:
    if isinstance(entity_slug, str):
        entity_model = EntityModel.objects.for_user(
            user_model=user_model).get(
            slug__exact=entity_slug)
    elif isinstance(entity_slug, EntityModel):
        entity_model = entity_slug
    else:
        raise ValidationError('entity_slug must be an instance of str or EntityModel')

    if not invoice_model.invoice_number:
        invoice_model.invoice_number = generate_invoice_number()
    ledger_model = LedgerModel.objects.create(
        entity=entity_model,
        posted=True,
        name=f'Invoice {invoice_model.invoice_number}'
    )
    ledger_model.clean()
    invoice_model.ledger = ledger_model
    return invoice_model


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


def set_default_unit(request, entity_model: EntityModel):
    pass


def get_default_entity_from_session(request):
    session_key = get_default_entity_session_key()
    return request.session.get(session_key)


def set_session_date_filter(request, entity_slug: str, end_date: date):
    session_key = get_end_date_session_key(entity_slug)
    request.session[session_key] = end_date.isoformat()


def generate_random_vendors(entity_model: EntityModel, fk):
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


def generate_random_customers(entity_model: EntityModel, fk):
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
                start_dt: date,
                accounts_gb: dict,
                cap_contribution: float or int):
    capital_acc = choice(accounts_gb['eq_capital'])
    cash_acc = choice(accounts_gb['asset_ca_cash'])

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

    ledger, created = entity_model.ledgers.get_or_create(
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


def generate_random_products(entity_model: EntityModel, uom_models, accounts_gb):
    product_count = randint(20, 40)
    product_models = [
        ItemModel(
            name=f'Product or Service {randint(1000, 9999)}',
            uom=choice(uom_models),
            sku=generate_random_sku(),
            upc=generate_random_upc(),
            item_id=generate_random_item_id(),
            entity=entity_model,
            is_product_or_service=True,
            earnings_account=choice(accounts_gb['in_sales']),
        ) for _ in range(product_count)
    ]

    product_models = entity_model.items.bulk_create(product_models)

    for im in product_models:
        im.clean()

    return product_models


def generate_random_expenses(entity_model: EntityModel, uom_models, accounts_gb):
    expense_count = randint(20, 40)
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

    expense_models = entity_model.items.bulk_create(expense_models)

    for em in expense_models:
        em.clean()

    return expense_models


def generate_random_invoice(
        entity_model: EntityModel,
        customer_models,
        user_model,
        is_progressible: bool,
        progress: float,
        accounts_by_role: dict,
        issue_dt: date,
        is_paid: bool,
        paid_dt: date,
        product_models):
    invoice_model = InvoiceModel(
        customer=choice(customer_models),
        progressible=is_progressible,
        progress=progress,
        terms=choice(InvoiceModel.TERMS)[0],
        invoice_number=generate_invoice_number(),
        amount_due=0,
        cash_account=choice(accounts_by_role['asset_ca_cash']),
        receivable_account=choice(accounts_by_role['asset_ca_recv']),
        payable_account=choice(accounts_by_role['lia_cl_acc_pay']),
        earnings_account=choice(accounts_by_role['in_sales']),
        date=issue_dt,
        paid=is_paid,
        paid_date=paid_dt
    )

    invoice_model = new_invoice_protocol(
        invoice_model=invoice_model,
        entity_slug=entity_model,
        user_model=user_model)

    invoice_model.clean()
    invoice_model.save()

    invoice_items = [
        InvoiceModelItemsThroughModel(
            invoice_model=invoice_model,
            item_model=choice(product_models),
            quantity=round(random() * randint(1, 5), 2),
            unit_cost=round(random() * randint(100, 999), 2)
        ) for _ in range(randint(1, 10))
    ]

    for ii in invoice_items:
        ii.clean()

    invoice_model.invoicemodelitemsthroughmodel_set.bulk_create(invoice_items)
    invoice_model.update_amount_due()
    invoice_model.amount_paid = Decimal(round(random() * float(invoice_model.amount_due), 2))
    invoice_model.new_state(commit=True)
    invoice_model.clean()
    invoice_model.save()
    invoice_model.migrate_state(
        user_model=user_model,
        entity_slug=entity_model.slug,
        je_date=paid_dt)


def generate_random_bill(
        entity_model: EntityModel,
        user_model,
        vendor_models: list,
        expense_models: list,
        is_progressible: bool,
        progress: float,
        accounts_by_role: dict,
        issue_dt: date,
        is_paid: bool,
        paid_dt: date):
    bill_model = BillModel(
        vendor=choice(vendor_models),
        progressible=is_progressible,
        progress=progress,
        terms=choice(BillModel.TERMS)[0],
        bill_number=generate_bill_number(),
        amount_due=0,
        cash_account=choice(accounts_by_role['asset_ca_cash']),
        receivable_account=choice(accounts_by_role['asset_ca_recv']),
        payable_account=choice(accounts_by_role['lia_cl_acc_pay']),
        earnings_account=choice(accounts_by_role['ex_op']),
        date=issue_dt,
        paid=is_paid,
        paid_date=paid_dt
    )

    bill_model = new_bill_protocol(
        bill_model=bill_model,
        entity_slug=entity_model,
        user_model=user_model)

    bill_model.clean()
    bill_model.save()

    bill_items = [
        BillModelItemsThroughModel(
            bill_model=bill_model,
            item_model=choice(expense_models),
            quantity=round(random() * randint(1, 5), 2),
            unit_cost=round(random() * randint(100, 800), 2)
        ) for _ in range(randint(1, 10))
    ]

    for ii in bill_items:
        ii.clean()

    bill_model.billmodelitemsthroughmodel_set.bulk_create(bill_items)
    bill_model.update_amount_due()
    bill_model.amount_paid = Decimal(round(random() * float(bill_model.amount_due), 2))
    bill_model.new_state(commit=True)
    bill_model.clean()
    bill_model.save()
    bill_model.migrate_state(
        user_model=user_model,
        entity_slug=entity_model.slug,
        je_date=paid_dt)


def generate_sample_data(entity_model: str or EntityModel,
                         user_model,
                         start_dt: datetime,
                         days_fw: int,
                         cap_contribution: float or int = 20000,
                         # income_tx_avg: float or int = 2000,
                         # expense_tx_avg: float or int = 1000,
                         tx_quantity: int = 100,
                         is_progressible_probability: float = 0.2,
                         is_paid_probability: float = 0.90):
    try:
        from faker import Faker
        from faker.providers import company, address, phone_number

        global FAKER_IMPORTED
        FAKER_IMPORTED = True

        fk = Faker(['en_US'])
        fk.add_provider(company)
        fk.add_provider(address)
        fk.add_provider(phone_number)

    except ImportError:
        return False

    if not isinstance(entity_model, EntityModel):
        entity_model: EntityModel = EntityModel.objects.get(slug__exact=entity_model)

    entity_model.ledgers.all().delete()
    entity_model.customers.all().delete()
    entity_model.vendors.all().delete()
    entity_model.items.all().delete()

    accounts = AccountModel.on_coa.for_entity_available(
        entity_slug=entity_model.slug,
        user_model=user_model
    ).order_by('role')
    accounts_by_role = {
        g: list(v) for g, v in groupby(accounts, key=lambda a: a.role)
    }

    vendor_models = generate_random_vendors(entity_model, fk)
    customer_models = generate_random_customers(entity_model, fk)

    # todo: create bank account models...
    fund_entity(entity_model=entity_model,
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

    loc_time = localtime()
    for i in range(tx_quantity):

        issue_dttm = start_dt + timedelta(days=randint(0, days_fw))
        if issue_dttm > loc_time:
            issue_dttm = loc_time

        is_progressible = random() < is_progressible_probability
        progress = Decimal(round(random(), 2)) if is_progressible else 0

        is_paid = random() < is_paid_probability
        paid_dttm = issue_dttm + timedelta(days=randint(0, 60)) if is_paid else None
        if paid_dttm and paid_dttm >= loc_time:
            paid_dttm = None
            is_paid = False

        issue_dt = issue_dttm.date()
        paid_dt = paid_dttm.date() if paid_dttm else None
        # switch_amt = random() > 0.75

        if i % 2 == 0:

            generate_random_bill(
                entity_model=entity_model,
                vendor_models=vendor_models,
                is_progressible=is_progressible,
                progress=progress,
                accounts_by_role=accounts_by_role,
                issue_dt=issue_dt,
                is_paid=is_paid,
                paid_dt=paid_dt,
                user_model=user_model,
                expense_models=expense_models
            )


        else:

            generate_random_invoice(
                entity_model=entity_model,
                customer_models=customer_models,
                is_progressible=is_progressible,
                progress=progress,
                accounts_by_role=accounts_by_role,
                issue_dt=issue_dt,
                is_paid=is_paid,
                paid_dt=paid_dt,
                user_model=user_model,
                product_models=product_models
            )


def progressible_net_summary(queryset: QuerySet) -> dict:
    """
    A convenience function that computes current net summary of progressible models.
    "net_30" group indicates the total amount is due in 30 days or less.
    "net_0" group indicates total past due amount.

    :param queryset: Progressible Objects Queryset.
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


def mark_progressible_paid(progressible_model: AccruableItemMixIn, user_model, entity_slug: str):
    progressible_model.paid = True
    progressible_model.clean()
    progressible_model.save()
    progressible_model.migrate_state(
        user_model=user_model,
        entity_slug=entity_slug
    )


def get_end_date_from_session(entity_slug: str, request) -> date:
    session_end_date_filter = get_end_date_session_key(entity_slug)
    end_date = request.session.get(session_end_date_filter)
    end_date = parse_date(end_date) if end_date else localdate()
    return end_date
