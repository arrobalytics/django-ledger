from django.apps.registry import apps


class IOCore:
    TXM = apps.get_model('django_ledger.TransactionModel', require_ready=False)
    ACM = apps.get_model('django_ledger.AccountModel', require_ready=False)

    def __init__(self, subject):
        self.subject = subject

        if self.subject.id:
            self.prop_manager = subject.prop_manager
            self.ledger = subject.prop_manager.forecast

    def get_subject_prop(self, key):
        return self.subject.get_prop(key)

    def get_ledger(self, scope='forecast'):
        return getattr(self.subject, scope)
