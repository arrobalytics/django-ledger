from django.urls import path

from django_ledger import views

urlpatterns = [
    path('my-dashboard/', views.DasboardView.as_view(), name='home'),
]
