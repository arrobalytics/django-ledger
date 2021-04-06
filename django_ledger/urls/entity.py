from django.urls import path

from django_ledger import views

urlpatterns = [
    # Entity Views ----
    path('list/', views.EntityModelListView.as_view(), name='entity-list'),
    path('create/', views.EntityModelCreateView.as_view(), name='entity-create'),

    # DASHBOARD Views...
    path('<slug:entity_slug>/detail/',
         views.EntityModelDetailView.as_view(),
         name='entity-dashboard'),
    path('<slug:entity_slug>/detail/year/<int:year>/',
         views.FiscalYearEntityModelDetailView.as_view(),
         name='entity-dashboard-year'),
    path('<slug:entity_slug>/detail/quarter/<int:year>/<int:quarter>/',
         views.QuarterlyEntityDetailView.as_view(),
         name='entity-dashboard-quarter'),
    path('<slug:entity_slug>/detail/month/<int:year>/<int:month>/',
         views.MonthlyEntityDetailView.as_view(),
         name='entity-dashboard-month'),
    path('<slug:entity_slug>/detail/date/<int:year>/<int:month>/<int:day>/',
         views.DateEntityDetailView.as_view(),
         name='entity-dashboard-date'),

    path('<slug:entity_slug>/update/', views.EntityModelUpdateView.as_view(), name='entity-update'),
    path('<slug:entity_slug>/delete/', views.EntityDeleteView.as_view(), name='entity-delete'),
    path('<slug:entity_slug>/set-date/', views.SetSessionDate.as_view(), name='entity-set-date'),

    # todo: DJL-122: Set Default Entity URL must have entity_slug KWARG
    path('set-default/', views.SetDefaultEntityView.as_view(), name='entity-set-default'),
]
