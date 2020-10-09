from django.urls import path

from django_ledger import views

urlpatterns = [
    path('home/', views.HomeView.as_view(), name='home'),
    path('', views.RootUrlView.as_view(), name='root'),
]
