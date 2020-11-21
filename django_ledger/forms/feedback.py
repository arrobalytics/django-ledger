from django import forms

from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES
from django.utils.translation import gettext_lazy as _


class BugReportForm(forms.Form):
    DEVICE_CHOICES = [
        ('desktop', _('Desktop')),
        ('tablet', _('Tablet')),
        ('mobile', _('Mobile'))
    ]

    reproduce = forms.CharField(
        label=_('How to reproduce?'),
        required=True,
        widget=forms.Textarea(attrs={
            'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' textarea',
            'rows': 3
        }))

    expectation = forms.CharField(
        label=_('What did you expect?'),
        required=True,
        widget=forms.Textarea(attrs={
            'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' textarea',
            'rows': 3
        }))

    device = forms.ChoiceField(
        choices=DEVICE_CHOICES,
        widget=forms.Select(attrs={
            'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
        }),
        required=True,
        label=_('What device are you using?'))


class RequestNewFeatureForm(forms.Form):
    feature_description = forms.CharField(
        label=_('Is your feature request related to a problem? Please describe.'),
        required=True,
        widget=forms.Textarea(attrs={
            'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' textarea',
            'rows': 3
        }))

    solution = forms.CharField(
        label=_('Describe the solution you\'d like'),
        required=True,
        widget=forms.Textarea(attrs={
            'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' textarea',
            'rows': 3
        }))

    alternatives = forms.CharField(
        label=_('Describe alternatives you\'ve considered'),
        widget=forms.Textarea(attrs={
            'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' textarea',
            'rows': 3
        }))
