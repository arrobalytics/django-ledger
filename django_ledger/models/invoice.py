from datetime import datetime

from django.db.models.signals import pre_save

from django_ledger.abstracts.invoice import InvoiceModelAbstract


class InvoiceModel(InvoiceModelAbstract):
    """
    Base InvoiceModel from Abstract
    """


def invoicemodel_presave(instance, sender, **kwargs):
    if not instance.date:
        instance.date = datetime.now().date()
    instance.clean()


pre_save.connect(invoicemodel_presave, InvoiceModel)
