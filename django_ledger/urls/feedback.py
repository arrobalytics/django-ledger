from django.urls import path
from django_ledger.views.feedback import BugReportView, RequestNewFeatureView

urlpatterns = [
    path('bug-report/', BugReportView.as_view(), name='bug-report'),
    path('new-feature/', RequestNewFeatureView.as_view(), name='new-feature')
]
