from django.urls import path
from fragview import views
from fragview.views import projects, datasets, hpc, results, density, misc


urlpatterns = [
    path('', misc.index, name='index'),

    path('testpage/', misc.testfunc, name='testpage'),

    path('datasets/', datasets.show_all, name='datasets'),
    path('dataset_info/', datasets.set_details, name='dataset_info'),

    path('results/', results.show, name='results'),

    path('density/', density.show, name='density'),
    path('dual_density/', density.compare_poses, name='dual_density'),
    path('pipedream_density/', density.show_pipedream, name='pipedream_density'),

    path('pandda_density/', density.pandda, name='pandda_density'),
    path('pandda_densityC/', density.pandda_consensus, name='pandda_densityC'),
    path('pandda/', views.pandda, name='pandda'),
    path('pandda_analyse/', views.pandda_analyse, name='pandda_analyse'),

    path('pandda_inspect/', views.pandda_inspect, name='pandda_inspect'),
    path('pandda_giant/', views.pandda_giant, name='pandda_giant'),

    path('pandda_notready/', views.pandda, name='pandda_notready'),
    path('pandda_running/', views.pandda, name='pandda_running'),

    path('submit_pandda/', views.submit_pandda, name='submit_pandda'),


    path('ugly/', misc.ugly, name='ugly'),
    path('reciprocal_lattice/', views.reciprocal_lattice, name='reciprocal_lattice'),
    path('dual_ligand_notready/', views.reciprocal_lattice, name='dual_ligand_notready'),

    path('procReport/', views.procReport, name='procReport'),
    path('results_download/', misc.results_download, name='results_download'),

    path('projects/', projects.list),
    path('project/<int:id>/', projects.edit),
    path('project/new', projects.new, name='new_project'),
    path('project/current/<int:id>/', projects.set_current),
    path('project_summary/', projects.project_summary, name='project_summary'),


    path('data_analysis/', views.data_analysis, name='data_analysis'),
    path('pipedream/', views.pipedream, name='pipedream'),
    path('pipedream_results/', views.pipedream_results, name='pipedream_results'),

    path('pipedream_results_notready/', views.pipedream_results, name='pipedream_results'),
    path('submit_pipedream/', views.submit_pipedream, name='submit_pipedream'),

    path('hpcstatus/', hpc.status, name='hpcstatus'),
    path('hpcstatus_jobkilled/', hpc.kill_job, name='hpcstatus_jobkilled'),

    path('dataproc_datasets/', views.dataproc_datasets, name='dataproc_datasets'),
    path('refine_datasets/', views.refine_datasets, name='refine_datasets'),
    path('ligfit_datasets/', views.ligfit_datasets, name='ligfit_datasets'),
]
