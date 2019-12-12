from django_ledger.model_base import load_model_abstract
from django_ledger.settings import DJANGO_LEDGER_SETTINGS

ChartOfAccountModelAbstract = load_model_abstract(DJANGO_LEDGER_SETTINGS.get('COA_MODEL_ABSTRACT'))


class ChartOfAccountModel(ChartOfAccountModelAbstract):
    """
    Base ChartOfAccounts Model
    """
