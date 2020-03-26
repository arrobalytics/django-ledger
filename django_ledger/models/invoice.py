from django.db.models.signals import post_delete

from django_ledger.abstracts.invoice import InvoiceModelAbstract


class InvoiceModel(InvoiceModelAbstract):
    """
    Base InvoiceModel from Abstract
    """


def invoicemodel_predelete(instance: InvoiceModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(invoicemodel_predelete, InvoiceModel)
