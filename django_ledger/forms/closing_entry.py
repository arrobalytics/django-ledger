from django.forms import DateInput, ValidationError, ModelForm
from django import forms
from django.utils.timezone import localdate

from django_ledger.models.closing_entry import ClosingEntryModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES
from django.utils.translation import gettext_lazy as _


class ClosingEntryCreateForm(ModelForm):

    def clean_closing_date(self):
        closing_date = self.cleaned_data['closing_date']
        if closing_date > localdate():
            raise ValidationError(
                message=_('Cannot create a closing entry with a future date.'), code='invalid_date'
            )
        return closing_date

    class Meta:
        model = ClosingEntryModel
        fields = [
            'closing_date'
        ]

        widgets = {
            'closing_date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                'placeholder': _('Closing Date (YYYY-MM-DD)...'),
                'id': 'djl-datepicker'
            })
        }
        labels = {
            'closing_date': _('Select a Closing Date')
        }
