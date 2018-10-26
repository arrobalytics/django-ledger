from django.urls import path
from books import views

app_name = 'books'

urlpatterns = [
    path('debug/', views.debug)
]
