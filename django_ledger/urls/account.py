from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/list/',
         views.AccountModelListView.as_view(),
         name='account-list'),
    path('<slug:entity_slug>/create/',
         views.AccountModelCreateView.as_view(),
         name='account-create'),
    path('<slug:entity_slug>/update/<uuid:account_pk>/',
         views.AccountModelUpdateView.as_view(),
         name='account-update'),
    path('<slug:entity_slug>/detail/<uuid:account_pk>/',
         views.AccountModelDetailView.as_view(),
         name='account-detail'),
    path('<slug:entity_slug>/detail/<uuid:account_pk>/year/<int:year>/',
         views.AccountModelYearDetailView.as_view(),
         name='account-detail-year'),
    path('<slug:entity_slug>/detail/<uuid:account_pk>/quarter/<int:year>/<int:quarter>/',
         views.AccountModelQuarterDetailView.as_view(),
         name='account-detail-quarter'),
    path('<slug:entity_slug>/detail/<uuid:account_pk>/month/<int:year>/<str:month>/',
         views.AccountModelMonthDetailView.as_view(),
         name='account-detail-month')
]
