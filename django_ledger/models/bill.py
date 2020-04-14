from django_ledger.abstracts.bill import BillModelAbstract


class BillModel(BillModelAbstract):
    REL_NAME_PREFIX = 'bill'
    """
    Bill Model
    """
