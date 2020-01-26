from django.forms import (ModelForm, Form, modelformset_factory, BaseModelFormSet, TextInput, Textarea, DateField,
                          BooleanField, Select, DateInput, ValidationError, ModelChoiceField, ChoiceField, CharField,
                          HiddenInput)
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from django_ledger.models import (AccountModel, LedgerModel, JournalEntryModel, TransactionModel,
                                  ChartOfAccountModel, EntityModel)
from django_ledger.models.mixins.io import validate_tx_data
from django_ledger.models_abstracts.journal_entry import ACTIVITIES

# todo: move this to settings & make it a list...
DJETLER_FORM_INPUT_CLASS = 'input'


class EntityModelDefaultForm(Form):
    entity_model = ModelChoiceField(
        queryset=EntityModel.objects.none(),
        widget=Select(attrs={
            'class': DJETLER_FORM_INPUT_CLASS,
            'id': 'djetler-set-entity-form-input'
            # 'onchange': 'setDefaultEntity()'
            # 'onchange': 'djetler.setDefaultEntity()'
        }))

    def __init__(self, *args, user_model, default_entity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.fields['entity_model'].queryset = EntityModel.objects.for_user(user=self.USER_MODEL).only('slug', 'name')
        if default_entity:
            self.initial = {
                'entity_model': default_entity
            }


class EntityModelUpdateForm(ModelForm):
    class Meta:
        model = EntityModel
        fields = [
            'name',
        ]
        labels = {
            'name': _l('Entity Name')
        }
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJETLER_FORM_INPUT_CLASS,
                    'placeholder': _l('Entity name...')
                }
            )
        }


class EntityModelCreateForm(ModelForm):
    populate_default_coa = BooleanField(required=False, label=_l('Populate Default CoA'))
    quickstart = BooleanField(required=False, label=_l('Use QuickStart Data'))

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError(_('Please provide a valid name for new Entity.'))
        if len(name) < 3:
            raise ValidationError(_('Looks like this entity name is too short...'))
        return name

    class Meta:
        model = EntityModel
        fields = [
            'name',
            'populate_default_coa',
            'quickstart'
        ]
        labels = {
            'name': _l('Entity Name'),
        }
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJETLER_FORM_INPUT_CLASS,
                    'placeholder': _l('Entity name...')
                }
            )
        }


class ChartOfAccountsModelForm(ModelForm):
    class Meta:
        model = ChartOfAccountModel
        fields = [
            'slug',
            'name',
            'description'
        ]
        labels = {
            'slug': _l('CoA ID'),
            'name': _l('Name'),
            'description': _l('Description'),
        }
        widgets = {
            'slug': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'name': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'description': Textarea(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
        }


class ChartOfAccountsModelUpdateForm(ModelForm):
    class Meta:
        model = ChartOfAccountModel
        fields = [
            'name',
            'locked'
        ]
        labels = {
            'name': _l('Name'),
            'description': _l('Description'),
        }
        widgets = {
            'name': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'description': Textarea(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
        }


class AccountModelBaseForm(ModelForm):

    def __init__(self, coa_slug, entity_slug, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.COA_SLUG = coa_slug
        self.ENTITY_SLUG = entity_slug
        self.fields['parent'].queryset = self.fields['parent'].queryset.filter(
            coa__slug__exact=self.COA_SLUG,
        ).order_by('code')


class AccountModelCreateForm(AccountModelBaseForm):

    def clean(self):
        parent = self.cleaned_data.get('parent')
        new_account_role = self.cleaned_data.get('role')
        cash_account = self.cleaned_data.get('cash_account')

        if parent:
            if all([
                parent,
                parent.role != new_account_role
            ]):
                raise ValidationError(_('Parent role must be the same as child account role.'))



        if all([
            cash_account,
            new_account_role != 'ca'
        ]):
            raise ValidationError(_('Cash account can ony be used on Current Assets.'))


    class Meta:
        model = AccountModel
        fields = [
            'parent',
            'code',
            'name',
            'role',
            'balance_type',
            'cash_account'
        ]
        widgets = {
            'parent': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'code': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'name': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'role': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'balance_type': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),

        }


class AccountModelUpdateForm(AccountModelBaseForm):
    class Meta:
        model = AccountModel
        fields = [
            'parent',
            'code',
            'name',
            'locked',
            'active'
        ]
        widgets = {
            'parent': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'code': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'name': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
        }


class LedgerModelCreateForm(ModelForm):
    class Meta:
        model = LedgerModel
        fields = [
            'name',
        ]
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJETLER_FORM_INPUT_CLASS
                }
            ),
        }


class LedgerModelUpdateForm(ModelForm):
    class Meta:
        model = LedgerModel
        fields = [
            'name',
            'posted',
            'locked',
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
        }


class JournalEntryModelCreateForm(ModelForm):
    def __init__(self, entity_slug, ledger_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.LEDGER_PK = ledger_pk

        # todo: move this method to model manager...
        self.fields['parent'].queryset = JournalEntryModel.on_coa.on_entity_posted(
            entity=self.ENTITY_SLUG
        ).filter(ledger_id=self.LEDGER_PK)

    class Meta:
        model = JournalEntryModel
        fields = [
            'parent',
            'activity',
            'date',
            'description'
        ]
        widgets = {
            'parent': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'activity': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'date': DateInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'description': Textarea(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            })
        }


class JournalEntryModelUpdateForm(JournalEntryModelCreateForm):
    class Meta:
        model = JournalEntryModel
        fields = [
            'parent',
            'activity',
            'date',
            'description',
            'locked',
            'posted'
        ]
        widgets = {
            'parent': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'activity': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'date': DateInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'description': Textarea(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            })
        }


class TransactionModelForm(ModelForm):
    class Meta:
        model = TransactionModel
        fields = [
            'account',
            'tx_type',
            'amount',
            'description'
        ]
        widgets = {
            'account': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS,
            }),
            'tx_type': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'amount': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'description': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
        }


class BaseTransactionModelFormSet(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.entity_slug = entity_slug
        for f in self.forms:
            f.fields['account'].queryset = AccountModel.on_coa.available(
                user=self.user
            ).filter(coa__entity__slug__exact=self.entity_slug).order_by('code')

    def clean(self):
        if any(self.errors):
            return
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
        txs_balances = [{
            'tx_type': tx.cleaned_data.get('tx_type'),
            'amount': tx.cleaned_data.get('amount')
        } for tx in self.forms if not self._should_delete_form(tx)]
        validate_tx_data(txs_balances)


TransactionModelFormSet = modelformset_factory(
    model=TransactionModel,
    form=TransactionModelForm,
    formset=BaseTransactionModelFormSet,
    can_delete=True,
    extra=5)


class ActivitySelectForm(Form):
    CHOICES = [('all', _l('All'))] + ACTIVITIES
    activity = ChoiceField(choices=CHOICES,
                           label=_l('Activity'),
                           initial='all',
                           widget=Select(
                               attrs={
                                   'class': DJETLER_FORM_INPUT_CLASS,
                                   'onchange': 'onBSActivitySelect'
                               }
                           ))


class AsOfDateForm(Form):
    entity_slug = CharField(max_length=150, widget=HiddenInput())
    date = DateField(widget=DateInput(
        attrs={
            'class': 'is-hidden',
            'data-input': True,
        }
    ))
