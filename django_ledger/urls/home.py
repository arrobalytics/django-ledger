from django.urls import path

from django_ledger import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
]
