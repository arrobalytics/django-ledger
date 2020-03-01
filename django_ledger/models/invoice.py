from django.db.models.signals import post_init, post_delete

from django_ledger.abstracts.invoice import InvoiceModelAbstract


class InvoiceModel(InvoiceModelAbstract):
    """
    Base InvoiceModel from Abstract
    """


def invoicemodel_postinit(instance: InvoiceModel, **kwargs):
    instance.DB_STATE = {
        'amount_paid': instance.amount_paid,
        'amount_receivable': instance.amount_receivable,
        'amount_unearned': instance.amount_unearned,
        'amount_earned': instance.amount_earned,
    }


post_init.connect(invoicemodel_postinit, InvoiceModel)


def invoicemodel_predelete(instance: InvoiceModel, **kwargs):
    instance.ledger.delete()


post_delete.connect(invoicemodel_predelete, InvoiceModel)
