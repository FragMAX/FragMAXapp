from django.urls import path
from fragview import views
from fragview.views import projects, datasets, hpc, results, density, misc, analysis, pandda


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

    path('pandda/', pandda.processing_form, name='pandda'),
    path('pandda_analyse/', pandda.analyse, name='pandda_analyse'),
    path('pandda_inspect/', pandda.inspect, name='pandda_inspect'),
    path('pandda_giant/', pandda.giant, name='pandda_giant'),
    path('submit_pandda/', pandda.submit, name='submit_pandda'),


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


    path('data_analysis/', analysis.processing_form, name='data_analysis'),
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
