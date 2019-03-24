from django.urls import path
from . import views


urlpatterns = [
    #path('', views.post_list, name='post_list'),
    path('', views.index, name='index'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/new/', views.post_new, name='post_new'),
    path('datasets/', views.datasets, name='datasets'),
    path('datasets_notready/', views.datasets, name='datasets_notready'),

    path('results/', views.results, name='results'),
    path('results_notready/', views.results, name='results_notready'),

    path('density/', views.request_page_res, name='density'),
    path('pandda_density/', views.request_page, name='pandda_density'),
    path('pandda/', views.pandda, name='pandda'),
    path('pandda_notready/', views.pandda, name='pandda_notready'),

    path('ugly/', views.ugly, name='ugly'),
    path('dual_ligand/', views.dual_ligand, name='dual_ligand'),
    path('dual_ligand_notready/', views.dual_ligand, name='dual_ligand_notready'),
    
    path('ligfit_results/', views.ligfit_results, name='ligfit_results'),
    path('dual_density/', views.compare_poses, name='dual_density'),
    path('project_summary/', views.load_project_summary, name='project_summary'),
    path('dataset_info/', views.dataset_info, name='dataset_info'),
    path('process_all/', views.process_all, name='process_all'),
    path('procReport/', views.procReport, name='procReport'),
    path('reproc_web/', views.reproc_web, name='reproc_web'),
    path('hpcstatus/', views.hpcstatus, name='hpcstatus'),
    path('hpcstatus_jobkilled/', views.kill_HPC_job, name='hpcstatus_jobkilled'),
    path('dataproc_merge/', views.dataproc_merge, name='dataproc_merge'),
    path('pipedream/', views.pipedream, name='pipedream'),
    path('project_summary_load/', views.project_summary_load, name='project_summary_load'),
    path('dataproc_datasets/', views.dataproc_datasets, name='dataproc_datasets'),
]