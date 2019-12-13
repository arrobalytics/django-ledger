from django.forms import ModelForm, Textarea, modelformset_factory, BaseModelFormSet

from django_ledger.models import (AccountModel, LedgerModel, JournalEntryModel, TransactionModel,
                                  ChartOfAccountModel, EntityModel)
from django_ledger.models.mixins.io import validate_tx_data


class EntityModelForm(ModelForm):
    class Meta:
        model = EntityModel
        fields = [
            'name',
        ]


class ChartOfAccountsModelForm(ModelForm):
    class Meta:
        model = ChartOfAccountModel
        fields = '__all__'


class AccountModelForm(ModelForm):
    class Meta:
        model = AccountModel
        fields = [
            'parent',
            'code',
            'name',
            'role',
            'balance_type',
        ]


class AccountModelCreateForm(ModelForm):
    class Meta:
        model = AccountModel
        fields = [
            'coa',
            'parent',
            'code',
            'name',
            'role',
            'balance_type',
        ]


class LedgerModelCreateForm(ModelForm):
    class Meta:
        model = LedgerModel
        fields = [
            'entity',
            'name',
        ]


class LedgerModelUpdateForm(ModelForm):
    class Meta:
        model = LedgerModel
        fields = [
            'entity',
            'name',
            'posted',
            'locked',
        ]


class JournalEntryModelForm(ModelForm):
    class Meta:
        model = JournalEntryModel
        fields = [
            'ledger',
            'parent',
            'activity',
            'date',
            'description'
        ]
        widgets = {
            'description': Textarea()
        }


class BaseTransactionModelFormSet(BaseModelFormSet):

    def clean(self):
        if any(self.errors):
            return
        txs_balances = [{
            'tx_type': tx.cleaned_data.get('tx_type'),
            'amount': tx.cleaned_data.get('amount')
        } for tx in self.forms]
        validate_tx_data(txs_balances)


TransactionModelFormSet = modelformset_factory(TransactionModel,
                                               formset=BaseTransactionModelFormSet,
                                               fields=('account', 'tx_type', 'amount', 'description'),
                                               extra=3)
