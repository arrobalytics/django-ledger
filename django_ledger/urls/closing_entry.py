from django.urls import path

from django_ledger import views

urlpatterns = [
    path('<slug:entity_slug>/list/', views.ClosingEntryModelListView.as_view(), name='closing-entry-list'),
]
