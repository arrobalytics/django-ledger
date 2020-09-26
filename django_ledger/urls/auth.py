from django.urls import path

from django_ledger import views

urlpatterns = [
    path('login/', views.DjangoLedgerLoginView.as_view(), name='login'),
    path('logout/', views.DjangoLedgerLogoutView.as_view(), name='logout'),
]
