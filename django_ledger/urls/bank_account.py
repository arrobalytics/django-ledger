from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/list/',
         views.BankAccountModelListView.as_view(),
         name='bank-account-list'),
    path('<slug:entity_slug>/create/',
         views.BankAccountModelCreateView.as_view(),
         name='bank-account-create'),
    path('<slug:entity_slug>/update/<uuid:bank_account_pk>/',
         views.BankAccountModelUpdateView.as_view(),
         name='bank-account-update'),

    # Actions...
    path('<slug:entity_slug>/action/<uuid:bank_account_pk>/mark-as-active/',
         views.BankAccountModelActionMarkAsActiveView.as_view(),
         name='bank-account-mark-as-active'),
    path('<slug:entity_slug>/action/<uuid:bank_account_pk>/mark-as-inactive/',
         views.BankAccountModelActionMarkAsInactiveView.as_view(),
         name='bank-account-mark-as-inactive')
]
