from django.urls import path
from django_ledger import views

urlpatterns = [
    # Entity Views ----
    path('list/', views.EntityModelListView.as_view(), name='entity-list'),
    path('create/', views.EntityModelCreateView.as_view(), name='entity-create'),

    path('<slug:entity_slug>/dashboard/',
         views.EntityDashboardView.as_view(),
         name='entity-dashboard'),
    path('<slug:entity_slug>/dashboard/year/<int:year>/',
         views.FiscalYearEntityModelDashboardView.as_view(),
         name='entity-dashboard-year'),
    path('<slug:entity_slug>/dashboard/quarter/<int:year>/<int:quarter>/',
         views.QuarterlyEntityDashboardView.as_view(),
         name='entity-dashboard-quarter'),
    path('<slug:entity_slug>/dashboard/month/<int:year>/<int:month>/',
         views.MonthlyEntityDashboardView.as_view(),
         name='entity-dashboard-month'),
    path('<slug:entity_slug>/dashboard/date/<int:year>/<int:month>/<int:day>/',
         views.DateEntityDashboardView.as_view(),
         name='entity-dashboard-date'),

    path('<slug:entity_slug>/update/', views.EntityModelUpdateView.as_view(), name='entity-update'),
    path('<slug:entity_slug>/delete/', views.EntityDeleteView.as_view(), name='entity-delete'),
    path('<slug:entity_slug>/set-date/', views.SetSessionDate.as_view(), name='entity-set-date'),
    path('set-default/', views.SetDefaultEntityView.as_view(), name='entity-set-default'),
]
