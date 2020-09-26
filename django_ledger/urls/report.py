from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/balance-sheet/',
         views.EntityModelBalanceSheetView.as_view(),
         name='entity-bs'),
    path('<slug:entity_slug>/income-statement/',
         views.EntityModelIncomeStatementView.as_view(),
         name='entity-ic'),
]
