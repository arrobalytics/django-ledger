from django.db import models
from django.utils.translation import gettext_lazy as _l

from django_ledger.abstracts.mixins.base import CreateUpdateMixIn, ProgressibleMixIn, LedgerPlugInMixIn


class BillModelAbstract(LedgerPlugInMixIn,
                        ProgressibleMixIn,
                        CreateUpdateMixIn):

    bill_number = models.SlugField(max_length=20, unique=True, verbose_name=_l('Invoice Number'))
