from django import forms


class OFXFileImportForm(forms.Form):
    ofx_file = forms.FileField(widget=forms.FileInput(attrs={
        'class': 'input'
    }))
