from django.urls import path

from . import views

app_name = 'django_ledger'

urlpatterns = [
    path('entity/', views.EntityModelListView.as_view(), name='entity-list'),
    path('entity/<slug:entity_slug>/', views.EntityModelDetailVew.as_view(), name='entity-detail'),
]
