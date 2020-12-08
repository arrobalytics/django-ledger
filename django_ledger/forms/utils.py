from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_cszc(cleaned_data):
    if any([
        cleaned_data['city'],
        cleaned_data['state'],
        cleaned_data['zip_code'],
        cleaned_data['country'],
    ]) and not all([
        cleaned_data['city'],
        cleaned_data['state'],
        cleaned_data['zip_code'],
        cleaned_data['country'],
    ]):
        raise ValidationError(message=_('Must provide all City/State/Zip/Country'))
