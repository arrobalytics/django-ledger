from django.urls import path
from django_ledger import views

urlpatterns = [
    # Entity Views ----
    path('list/', views.EntityModelListView.as_view(), name='entity-list'),
    path('create/', views.EntityModelCreateView.as_view(), name='entity-create'),
    path('<slug:entity_slug>/dashboard/', views.EntityModelDashboardView.as_view(), name='entity-dashboard'),
    path('<slug:entity_slug>/update/', views.EntityModelUpdateView.as_view(), name='entity-update'),
    path('<slug:entity_slug>/delete/', views.EntityDeleteView.as_view(), name='entity-delete'),
    path('<slug:entity_slug>/set-date/', views.SetDateView.as_view(), name='entity-set-date'),
    path('set-default/', views.SetDefaultEntityView.as_view(), name='entity-set-default'),
]
