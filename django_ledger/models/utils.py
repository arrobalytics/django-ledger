from datetime import datetime, timedelta
from itertools import groupby
from random import choice, random, randint

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from django_ledger.models.accounts import AccountModel
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.bill import BillModel
from django_ledger.models.bill import generate_bill_number
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.invoice import generate_invoice_number
from django_ledger.models.ledger import LedgerModel

UserModel = get_user_model()


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
                         cap_contribution: float or int = 10000,
                         income_tx_avg: float or int = 2000,
                         expense_tx_avg: float or int = 1000,
                         tx_quantity: int = 200):
    """
    TXS = List[{
            'account_id': Account Database UUID
            'tx_type': credit/debit,
            'amount': Decimal/Float/Integer,
            'description': string,
            'staged_tx_model': StagedTransactionModel or None
        }]
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

    if not isinstance(entity, EntityModel):
        entity = EntityModel.objects.get(slug__exact=entity)
    accounts = AccountModel.on_coa.for_entity_available(
        entity_slug=entity.slug,
        user_model=user_model
    ).order_by('role')

    accounts_gb = {
        g: list(v) for g, v in groupby(accounts, key=lambda a: a.role)
    }

    capital_acc = choice(accounts_gb['eq_capital'])
    cash_acc = choice(accounts_gb['asset_ca_cash'])
    ledger = entity.ledgers.first()
    ledger.journal_entries.all().delete()

    txs = list()
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
    entity.commit_txs(je_date=start_dt,
                      je_txs=txs,
                      je_activity='op',
                      je_posted=True,
                      je_ledger=ledger)

    rng = tx_quantity
    for i in range(rng):
        txs = list()
        dt = start_dt + timedelta(days=randint(0, days_fw))
        if i % 2 == 0:
            exp_amt = random() * expense_tx_avg
            txs.append({
                'account_id': cash_acc.uuid,
                'tx_type': 'credit',
                'amount': exp_amt,
                'description': f'Sample data for {entity.name}'
            })

            exp_acc = choice(accounts_gb['ex_op'])
            txs.append({
                'account_id': exp_acc.uuid,
                'tx_type': 'debit',
                'amount': exp_amt,
                'description': f'Sample data for {entity.name}'
            })
        else:
            in_amt = random() * income_tx_avg
            txs.append({
                'account_id': cash_acc.uuid,
                'tx_type': 'debit',
                'amount': in_amt,
                'description': f'Sample data for {entity.name}'
            })

            in_acc = choice(accounts_gb['in_sales'])
            txs.append({
                'account_id': in_acc.uuid,
                'tx_type': 'credit',
                'amount': in_amt,
                'description': f'Sample data for {entity.name}'
            })

        print(f'TXS: {i + 1}/{rng} created...')
        entity.commit_txs(je_date=dt,
                          je_txs=txs,
                          je_activity='op',
                          je_posted=True,
                          je_ledger=ledger)


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
