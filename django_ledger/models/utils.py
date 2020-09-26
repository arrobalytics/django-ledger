from datetime import datetime, timedelta
from decimal import Decimal
from itertools import groupby
from random import choice, random, randint

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.utils.timezone import localtime

from django_ledger.models.accounts import AccountModel
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.bill import BillModel
from django_ledger.models.bill import generate_bill_number
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.invoice import generate_invoice_number
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.mixins import ProgressibleMixIn

UserModel = get_user_model()
FAKER_IMPORTED = False


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


def populate_default_coa(entity_model: EntityModel):
    acc_objs = [AccountModel(
        code=a['code'],
        name=a['name'],
        role=a['role'],
        balance_type=a['balance_type'],
        coa=entity_model.coa,
    ) for a in CHART_OF_ACCOUNTS]

    for acc in acc_objs:
        acc.full_clean()
        acc.save()


def make_accounts_active(entity_model: EntityModel, account_code_set: set):
    accounts = entity_model.coa.accounts.filter(code__in=account_code_set)
    accounts.update(active=True)


def get_date_filter_session_key(entity_slug: str):
    # todo: rename this key...
    return f'dj_ledger_entity_{entity_slug}_date_filter'.replace('-', '_')


def get_default_entity_session_key():
    # todo: rename this key...
    return 'dj_ledger_default_entity_id'


def generate_sample_data(entity: str or EntityModel,
                         user_model,
                         start_dt: datetime,
                         days_fw: int,
                         cap_contribution: float or int = 20000,
                         income_tx_avg: float or int = 2000,
                         expense_tx_avg: float or int = 1000,
                         tx_quantity: int = 100,
                         is_progressible_probability: float = 0.2,
                         is_paid_probability: float = 0.97):
    """
    TXS = List[{
            'account_id': Account Database UUID
            'tx_type': credit/debit,
            'amount': Decimal/Float/Integer,
            'description': string,
            'staged_tx_model': StagedTransactionModel or None
        }]
    :param is_paid_probability:
    :param is_progressible_probability:
    :param tx_quantity:
    :param expense_tx_avg:
    :param income_tx_avg:
    :param cap_contribution:
    :param days_fw:
    :param start_dt:
    :param user_model:
    :param entity:
    :return:
    """

    try:
        from faker import Faker
        from faker.providers import company, address, phone_number
        global FAKER_IMPORTED
        FAKER_IMPORTED = True
    except ImportError:
        return False

    if not isinstance(entity, EntityModel):
        entity = EntityModel.objects.get(slug__exact=entity)

    entity.ledgers.all().delete()

    ledger, created = entity.ledgers.get_or_create(
        name='Sample Data Ledger',
        posted=True
    )

    accounts = AccountModel.on_coa.for_entity_available(
        entity_slug=entity.slug,
        user_model=user_model
    ).order_by('role')

    accounts_gb = {
        g: list(v) for g, v in groupby(accounts, key=lambda a: a.role)
    }

    capital_acc = choice(accounts_gb['eq_capital'])
    cash_acc = choice(accounts_gb['asset_ca_cash'])

    txs = list()

    fk = Faker()
    fk.add_provider(company)
    fk.add_provider(address)
    fk.add_provider(phone_number)

    txs.append({
        'account_id': cash_acc.uuid,
        'tx_type': 'debit',
        'amount': cap_contribution,
        'description': f'Sample data for {entity.name}'
    })
    txs.append({
        'account_id': capital_acc.uuid,
        'tx_type': 'credit',
        'amount': cap_contribution,
        'description': f'Sample data for {entity.name}'
    })

    entity.commit_txs(
        je_date=start_dt,
        je_txs=txs,
        je_activity='op',
        je_posted=True,
        je_ledger=ledger
    )

    loc_time = localtime()
    rng = tx_quantity
    for i in range(rng):

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
        switch_amt = random() > 0.75

        if i % 2 == 0:

            amt = expense_tx_avg if not switch_amt else income_tx_avg
            bill_amt = Decimal(round(random() * amt, 2))
            bill_amt_paid = Decimal(round(Decimal(random()) * bill_amt, 2))

            bill = BillModel(
                bill_to=fk.name() if random() > .5 else fk.company(),
                address_1=fk.address(),
                phone=fk.phone_number(),
                email=fk.email(),
                website=fk.url(),
                progressible=is_progressible,
                progress=progress,
                terms=choice(BillModel.TERMS)[0],
                xref=generate_bill_number(length=15, prefix=False),
                cash_account=choice(accounts_gb['asset_ca_cash']),
                receivable_account=choice(accounts_gb['asset_ca_recv']),
                payable_account=choice(accounts_gb['lia_cl_acc_pay']),
                earnings_account=choice(accounts_gb['ex_op']),
                amount_due=bill_amt,
                amount_paid=bill_amt_paid,
                date=issue_dt,
                paid=is_paid,
                paid_date=paid_dt
            )

            bill = new_bill_protocol(bill_model=bill, entity_slug=entity.slug, user_model=user_model)
            bill.clean()
            bill.migrate_state(user_model=user_model, entity_slug=entity.slug, je_date=paid_dt)
            bill.save()
            print(f'Bill {bill.bill_number} created...')

        else:

            amt = income_tx_avg if not switch_amt else expense_tx_avg
            inv_amt = Decimal(round(random() * amt, 2))
            inv_amt_paid = Decimal(round(Decimal(random()) * inv_amt, 2))

            invoice = InvoiceModel(
                invoice_to=fk.name() if random() > .5 else fk.company(),
                address_1=fk.address(),
                phone=fk.phone_number(),
                email=fk.email(),
                website=fk.url(),
                progressible=is_progressible,
                progress=progress,
                terms=choice(InvoiceModel.TERMS)[0],
                invoice_number=generate_invoice_number(),
                cash_account=choice(accounts_gb['asset_ca_cash']),
                receivable_account=choice(accounts_gb['asset_ca_recv']),
                payable_account=choice(accounts_gb['lia_cl_acc_pay']),
                earnings_account=choice(accounts_gb['in_sales']),
                amount_due=inv_amt,
                amount_paid=inv_amt_paid,
                date=issue_dt,
                paid=is_paid,
                paid_date=paid_dt
            )

            invoice = new_invoice_protocol(
                invoice_model=invoice,
                entity_slug=entity.slug,
                user_model=user_model)

            invoice.clean()
            invoice.migrate_state(user_model=user_model, entity_slug=entity.slug, je_date=paid_dt)
            invoice.save()
            print(f'Invoice {invoice.invoice_number} created...')


def progressible_net_summary(queryset: QuerySet) -> dict:
    """
    A convenience function that computes current net summary of progressible items.
    "net_30" group indicates the total amount is due in 30 days or less.
    "net_0" group indicates total past due amount.

    :param queryset: Progressible Objects Queryset.
    :return: A dictionary summarizing current net summary 0,30,60,90,90+ bill open amounts.
    """
    bill_nets = [{
        'net_due_group': b.net_due_group(),
        'amount_open': b.get_amount_open()
    } for b in queryset]
    bill_nets.sort(key=lambda b: b['net_due_group'])
    return {
        g: float(sum(b['amount_open'] for b in l)) for g, l in groupby(bill_nets, key=lambda b: b['net_due_group'])
    }


def mark_progressible_paid(progressible_model: ProgressibleMixIn, user_model, entity_slug: str):
    progressible_model.paid = True
    progressible_model.clean()
    progressible_model.save()
    progressible_model.migrate_state(
        user_model=user_model,
        entity_slug=entity_slug
    )
