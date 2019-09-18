from django.urls import path
from . import views


urlpatterns = [
    #path('', views.post_list, name='post_list'),
    path('', views.index, name='index'),


    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/new/', views.post_new, name='post_new'),
    path('error/', views.error_page, name="error page"),


    path('testpage/', views.testfunc, name='pandda_analyse'),
    path('datasets/', views.datasets, name='datasets'),
    path('datasets_notready/', views.datasets, name='datasets_notready'),


    path('settings/', views.settings, name='settings'),
    path('results/', views.results, name='results'),
    path('results_notready/', views.results, name='results_notready'),

    path('density/', views.results_density, name='density'),
    path('pipedream_density/', views.load_pipedream_density, name='pipedream_density'),

    path('pandda_density/', views.pandda_density, name='pandda_density'),
    path('pandda_densityC/', views.pandda_densityC, name='pandda_densityC'),
    path('pandda/', views.pandda, name='pandda'),
    path('pandda_analyse/', views.pandda_analyse, name='pandda_analyse'),

    path('pandda_inspect/', views.pandda_inspect, name='pandda_inspect'),
    path('pandda_giant/', views.pandda_giant, name='pandda_giant'),

    path('pandda_notready/', views.pandda, name='pandda_notready'),
    path('pandda_running/', views.pandda, name='pandda_running'),

    path('submit_pandda/', views.submit_pandda, name='submit_pandda'),


    path('ugly/', views.ugly, name='ugly'),
    path('reciprocal_lattice/', views.reciprocal_lattice, name='reciprocal_lattice'),
    path('dual_ligand_notready/', views.reciprocal_lattice, name='dual_ligand_notready'),
    path('dual_density/', views.compare_poses, name='dual_density'),

    path('ligfit_results/', views.ligfit_results, name='ligfit_results'),
    path('procReport/', views.procReport, name='procReport'),
    path('results_download/', views.results_download, name='results_download'),
    

    path('project_summary/', views.load_project_summary, name='project_summary'),
    # path('project_summary_load/', views.project_summary_load, name='project_summary_load'),

    path('dataset_info/', views.dataset_info, name='dataset_info'),
    path('data_analysis/', views.data_analysis, name='data_analysis'),
    path('pipedream/', views.pipedream, name='pipedream'),
    path('pipedream_results/', views.pipedream_results, name='pipedream_results'),

    path('pipedream_results_notready/', views.pipedream_results, name='pipedream_results'),


    path('submit_pipedream/', views.submit_pipedream, name='submit_pipedream'),
    path('reproc_web/', views.reproc_web, name='reproc_web'),

    path('hpcstatus/', views.hpcstatus, name='hpcstatus'),
    path('hpcstatus_jobkilled/', views.kill_HPC_job, name='hpcstatus_jobkilled'),
    path('dataproc_merge/', views.dataproc_merge, name='dataproc_merge'),
    
    path('dataproc_datasets/', views.dataproc_datasets, name='dataproc_datasets'),
    path('refine_datasets/', views.refine_datasets, name='refine_datasets'),
    path('ligfit_datasets/', views.ligfit_datasets, name='ligfit_datasets'),


]