from django.contrib.auth import get_user_model

from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa_default import CHART_OF_ACCOUNTS
from django_ledger.models.entity import EntityModel

UserModel = get_user_model()


# def txs_digest(tx: dict) -> dict:
#     tx['role_bs'] = BS_ROLES.get(tx['account__role'])
#     if tx['account__balance_type'] != tx['tx_type']:
#         tx['amount'] = -tx['amount']
#     if tx['account__balance_type'] != ACCOUNT_CONVENTION.get(tx['role_bs']):
#         tx['amount'] = -tx['amount']
#     return tx


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
    return f'djetler_entity_{entity_slug}_date_filter'.replace('-', '_')


def get_default_entity_session_key():
    return 'djetler_default_entity_id'
