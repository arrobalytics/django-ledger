"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.core.mail import send_mail
from django.views.generic import FormView

from django_ledger.forms.feedback import BugReportForm, RequestNewFeatureForm
from django_ledger.settings import DJANGO_LEDGER_FEEDBACK_EMAIL_LIST, DJANGO_LEDGER_FEEDBACK_FROM_EMAIL
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, SuccessUrlNextMixIn


class BugReportView(DjangoLedgerSecurityMixIn,
                    SuccessUrlNextMixIn,
                    FormView):
    http_method_names = ['post']
    form_class = BugReportForm

    def form_valid(self, form):
        form_data = form.cleaned_data
        message = f'How to reproduce?: {form_data["reproduce"]}\n' + \
                  f'Expectation: {form_data["expectation"]}\n' + \
                  f'Device: {form_data["device"]}\n' + \
                  f'From user: {self.request.user.username}\n' + \
                  f'User email: {self.request.user.email}'
        if DJANGO_LEDGER_FEEDBACK_EMAIL_LIST:
            send_mail(
                subject=f'DJL Bug Report',
                from_email=DJANGO_LEDGER_FEEDBACK_FROM_EMAIL,
                recipient_list=DJANGO_LEDGER_FEEDBACK_EMAIL_LIST,
                fail_silently=True,
                message=message)
        return super().form_valid(form)


class RequestNewFeatureView(DjangoLedgerSecurityMixIn,
                            SuccessUrlNextMixIn,
                            FormView):
    http_method_names = ['post']
    form_class = RequestNewFeatureForm

    def form_valid(self, form):
        form_data = form.cleaned_data
        message = f'Description: {form_data["feature_description"]}\n' + \
                  f'Solution: {form_data["solution"]}\n' + \
                  f'Alternatives: {form_data["alternatives"]}\n' + \
                  f'From user: {self.request.user.username}\n' + \
                  f'User email: {self.request.user.email}'
        if DJANGO_LEDGER_FEEDBACK_EMAIL_LIST:
            send_mail(
                subject=f'DJL New Feature Request',
                from_email=DJANGO_LEDGER_FEEDBACK_FROM_EMAIL,
                recipient_list=DJANGO_LEDGER_FEEDBACK_EMAIL_LIST,
                fail_silently=True,
                message=message)
        return super().form_valid(form)
