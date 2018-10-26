from django.db import models


class LedgerMixIn(models.Model):
    entity = models.ForeignKey('books.EntityModel', on_delete=models.CASCADE)
    ledgers = models.ManyToManyField('books.LedgerModel')

    def ledgers_init(self):
        actuals_ledger, created = self.ledgers.get_or_create(scope='a',
                                                             entity=getattr(self, 'entity'))
        setattr(self, 'actuals', actuals_ledger)

        forecast_ledger, created = self.ledgers.get_or_create(scope='f',
                                                              entity=getattr(self, 'entity'))
        setattr(self, 'forecast', forecast_ledger)

        baseline_ledger, created = self.ledgers.get_or_create(scope='b',
                                                              entity=getattr(self, 'entity'))
        setattr(self, 'baseline', baseline_ledger)

    class Meta:
        abstract = True
