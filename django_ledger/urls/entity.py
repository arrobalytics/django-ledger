from django.urls import path
from django_ledger import views

urlpatterns = [
    # Entity Views ----
    path('', views.EntityModelListView.as_view(), name='entity-list'),
    path('create/', views.EntityModelCreateView.as_view(), name='entity-create'),
    path('set-default/', views.SetDefaultEntityView.as_view(), name='entity-set-default'),
    path('<slug:entity_slug>/dashboard/', views.EntityModelDashboardView.as_view(), name='entity-dashboard'),
    path('<slug:entity_slug>/manage/', views.EntityModelManageView.as_view(), name='entity-manage'),
    path('<slug:entity_slug>/set-date/', views.SetDateView.as_view(), name='entity-set-date'),
    path('<slug:entity_slug>/generate-sample-data/', views.GenerateSampleData.as_view(), name='entity-gen-sample-data'),
]
