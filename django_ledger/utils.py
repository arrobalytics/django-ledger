"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import date
from importlib import import_module
from itertools import groupby
from random import choice
from string import ascii_uppercase, ascii_lowercase, digits

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet
from django.utils.dateparse import parse_date

from django_ledger.io.io_core import get_localdate

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


def get_end_date_session_key(entity_slug: str):
    return f'djl_end_date_filter_{entity_slug}'.replace('-', '_')


def get_default_entity_session_key():
    return 'djl_default_entity_model'


def get_default_unit_session_key():
    return 'djl_default_unit_model'


def set_default_entity(request, entity_model):
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


def get_end_date_from_session(entity_slug: str, request) -> date:
    session_end_date_filter = get_end_date_session_key(entity_slug)
    end_date = request.session.get(session_end_date_filter)
    end_date = parse_date(end_date) if end_date else get_localdate()
    return end_date
