from django.urls import path
from . import views


urlpatterns = [
    #path('', views.post_list, name='post_list'),
    path('', views.index, name='index'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/new/', views.post_new, name='post_new'),
    path('datasets/', views.datasets, name='datasets'),
    path('results/', views.results, name='results'),
    path('density/', views.request_page_res, name='density'),
    path('pandda_density/', views.request_page, name='pandda_density'),
    path('pandda/', views.pandda, name='pandda'),
    path('ugly/', views.ugly, name='ugly'),
    path('dual_ligand/', views.dual_ligand, name='dual_ligand'),
    path('ligfit_results/', views.ligfit_results, name='ligfit_results'),
    path('dual_density/', views.compare_poses, name='dual_density'),
    path('project_summary/', views.load_project_summary, name='project_summary'),
    path('dataset_info/', views.dataset_info, name='dataset_info'),
    path('process_all/', views.process_all, name='process_all'),
    path('procReport/', views.procReport, name='procReport'),
    path('test/', views.test, name='test'),
]