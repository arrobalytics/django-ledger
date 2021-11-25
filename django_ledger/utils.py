from datetime import date
from itertools import groupby
from random import choice
from string import ascii_uppercase, ascii_lowercase, digits
from typing import Tuple

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.utils.timezone import localdate

from django_ledger.models import (AccruableItemMixIn, generate_po_number, PurchaseOrderModel, EntityModel,
                                  LedgerModel, BankAccountModel, AccountModel)
from django_ledger.models import generate_invoice_number, InvoiceModel, generate_bill_number, BillModel
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS

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
