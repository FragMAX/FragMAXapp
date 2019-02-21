from django.urls import path
from . import views


urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/new/', views.post_new, name='post_new'),
    path('datasets/', views.datasets, name='datasets'),
    path('results/', views.results, name='results'),
    path('density/', views.request_page, name='density'),
    path('pandda/', views.pandda, name='pandda'),
    path('ugly/', views.ugly, name='ugly'),



]