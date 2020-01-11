from random import randint

from django.contrib.auth import get_user_model
from django.utils.text import slugify

from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import populate_default_coa, make_accounts_active

UserModel = get_user_model()


def quickstart(user_model: str or UserModel,
               entity_model: str or EntityModel = None,
               txs_data: list = None):
    """
    Utility function to populate initial data. User must be in database.
    Creates a new entity every time function is run.
    :param user_model: A string representing the username or an instance of UserModel.
    :param entity_model: A string representing the name of the entity or an instance of EntityModel.
    :param txs_data: A list of dictionaries for the new quickstart ledger. Credits and debits will be validated.

    Example:

        txs_data = [
            {
                'code': '1010',
                'amount': 200000,
                'tx_type': 'debit',
                'description': 'Company Funding'
            },
            {
                'code': '3010',
                'amount': 200000,
                'tx_type': 'credit',
                'description': 'Capital contribution'
            } ....... ]
    :return:
    """
    if not isinstance(user_model, UserModel):
        user_model = UserModel.objects.get(username=user_model)

    if not isinstance(entity_model, EntityModel):
        rand_int = randint(10000, 99999)
        entity_name = f'My Quickstart Inc - {rand_int}'
        entity_slug = slugify(entity_name)
        entity_model = EntityModel.objects.create(name=entity_name,
                                                  slug=entity_slug,
                                                  admin=user_model)
    populate_default_coa(entity_model=entity_model)

    if not txs_data:
        txs_data = [
            {
                'je_date': '2019-10-01',
                'je_origin': 'djetler-quickstart',
                'je_desc': 'Purchase of property at 123 Main St',
                'je_activity': 'other',
                'je_posted': True,
                'je_txs': [
                    {
                        'code': '1010',
                        'amount': 200000,
                        'tx_type': 'debit',
                        'description': 'Capital contribution'
                    },
                    {
                        'code': '3010',
                        'amount': 200000,
                        'tx_type': 'credit',
                        'description': 'Capital contribution'
                    }
                ]
            },
            {
                'je_date': '2019-10-20',
                'je_origin': 'djetler-quickstart',
                'je_desc': 'Purchase of property at 123 Main St',
                'je_activity': 'inv',
                'je_posted': True,
                'je_txs': [
                    {
                        'code': '1010',
                        'amount': 40000,
                        'tx_type': 'credit',
                        'description': 'Downpayment'
                    },
                    {
                        'code': '2110',
                        'amount': 80000,
                        'tx_type': 'credit',
                        'description': 'Issue debt'
                    },
                    {
                        'code': '1610',
                        'amount': 120000,
                        'tx_type': 'debit',
                        'description': 'Property cost base'
                    },
                ]
            },
            {
                'je_date': '2019-10-31',
                'je_origin': 'djetler-quickstart',
                'je_desc': 'Purchase of property at 123 Main St',
                'je_activity': 'inv',
                'je_posted': True,
                'je_txs': [
                    {
                        'code': '1611',
                        'amount': 465.50,
                        'tx_type': 'credit',
                        'description': 'Accumulated Depreciation'
                    },
                    {
                        'code': '6070',
                        'amount': 465.50,
                        'tx_type': 'debit',
                        'description': 'Accumulated Depreciation'
                    },
                ]
            },
            {
                'je_date': '2019-11-30',
                'je_origin': 'djetler-quickstart',
                'je_desc': 'Purchase of property at 123 Main St',
                'je_activity': 'op',
                'je_posted': True,
                'je_txs': [
                    {
                        'code': '1010',
                        'amount': 1500,
                        'tx_type': 'debit',
                        'description': 'Rental Income'
                    },
                    {
                        'code': '4020',
                        'amount': 1500,
                        'tx_type': 'credit',
                        'description': 'Rental Income'
                    },
                    {
                        'code': '1010',
                        'amount': 180.45,
                        'tx_type': 'credit',
                        'description': 'HOA expense'
                    },                    {
                        'code': '6253',
                        'amount': 180.45,
                        'tx_type': 'debit',
                        'description': 'HOA expense'
                    },
                ]
            },
        ]

        txs_data_codes = set(sum([[tx['code'] for tx in je['je_txs']] for je in txs_data], []))
        make_accounts_active(entity_model=entity_model, account_code_set=txs_data_codes)

        general_ledger = entity_model.ledgers.get(name__exact='General Ledger')

        for je in txs_data:
            je['je_ledger'] = general_ledger
            entity_model.create_je(**je)
