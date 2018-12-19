from django.db import models

LEDGER_SCOPES = {
    'f': 'forecast',
    'b': 'baseline',
}


class LedgerMixIn(models.Model):
    ledgers = models.ManyToManyField('django_ledger.LedgerModel')

    def _ledger_entity(self):
        return getattr(self, 'entity')

    def ledgers_init(self):
        actuals_ledger, created = self.ledgers.get_or_create(scope='a',
                                                             entity=self._ledger_entity())
        setattr(self, 'actuals', actuals_ledger)

        for s, l in LEDGER_SCOPES.items():
            ledger, created = self.ledgers.get_or_create(scope=s,
                                                         entity=self._ledger_entity())
            setattr(self, l, ledger)

    class Meta:
        abstract = True
