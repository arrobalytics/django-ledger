from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/list/',
         views.AccountModelListView.as_view(),
         name='account-list'),
    path('<slug:entity_slug>/list/active/',
         views.AccountModelListView.as_view(active_only=True),
         name='account-list-active'),
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
    path('<slug:entity_slug>/detail/<uuid:account_pk>/month/<int:year>/<int:month>/',
         views.AccountModelMonthDetailView.as_view(),
         name='account-detail-month'),
    path('<slug:entity_slug>/detail/<uuid:account_pk>/date/<int:year>/<int:month>/<int:day>/',
         views.AccountModelDateDetailView.as_view(),
         name='account-detail-date'),

    # Actions...
    path('<slug:entity_slug>/action/<uuid:account_pk>/activate/',
         views.AccountModelModelActionView.as_view(action_name='activate'),
         name='account-action-activate'),
    path('<slug:entity_slug>/action/<uuid:account_pk>/deactivate/',
         views.AccountModelModelActionView.as_view(action_name='deactivate'),
         name='account-action-deactivate'),

]
