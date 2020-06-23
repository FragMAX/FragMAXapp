from django.urls import path
from fragview.views import projects, datasets, hpc, results, density, misc, analysis, pandda, reciprocal, soaking, pdbs
from fragview.views import pipedream, refine, process, ligfit, diffraction, ccp4, fragment, crypt, result_pdbs
from fragview.views import encryption, download


urlpatterns = [
    # use 'project summary' view as the landing page
    path('', projects.project_summary, name='project_summary'),
    path('log_viewer/', misc.log_viewer, name='log_viewer'),

    path('testpage/', misc.testfunc, name='testpage'),

    path('soaking_plan/', soaking.soaking_plan, name='soaking_plan'),

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
    path('reciprocal_lattice/<sample>/<run>', reciprocal.show, name='reciprocal_lattice'),

    path('procReport/', datasets.proc_report, name='procReport'),
    path('project_details/', misc.project_details, name='project_details'),
    path('library_view/', misc.library_view, name='library_view'),
    path('download_options/', misc.download_options, name='download_options'),

    # project management views
    path('projects/', projects.show, name='manage_projects'),
    path('project/<int:id>/', projects.edit),
    path('project/new', projects.new, name='new_project'),
    path('project/current/<int:id>/', projects.set_current),

    # encryption key management views
    path('encryption/', encryption.show, name='encryption'),
    path('encryption/key/', encryption.download_key),
    path('encryption/key/upload/', encryption.upload_key),
    path('encryption/key/forget/', encryption.forget_key),

    # PDBs management views
    path('pdbs/', pdbs.list, name='manage_pdbs'),
    path('pdb/<int:id>', pdbs.edit),
    path('pdb/add', pdbs.add),
    path('pdb/new', pdbs.new),

    # download views
    path('download/', download.page),
    path('download/pandda', download.pandda),

    # generated PDB access views
    path('pdbs/final/<dataset>/<process>/<refine>', result_pdbs.final),

    path('data_analysis/', analysis.processing_form, name='data_analysis'),

    path('pipedream/', pipedream.processing_form, name='pipedream'),
    path('pipedream_results/', pipedream.results, name='pipedream_results'),
    path('submit_pipedream/', pipedream.submit, name='submit_pipedream'),

    path('hpcstatus/', hpc.status, name='hpcstatus'),
    path('hpcstatus_jobkilled/', hpc.kill_job, name='hpcstatus_jobkilled'),
    path('jobhistory/', hpc.jobhistory, name='jobhistory'),

    path('dataproc_datasets/', process.datasets, name='dataproc_datasets'),
    path('refine_datasets/', refine.datasets, name='refine_datasets'),
    path('ligfit_datasets/', ligfit.datasets, name='ligfit_datasets'),

    path('diffraction/<dataset>/<run>/<int:image_num>', diffraction.image, name='diffraction_image'),
    path('ccp4_map/<dataset>/<process>/<refine>/<type>', ccp4.map),
    path('pipedream_ccp4_map/<sample>/<process>/<type>', ccp4.pipedream_map),
    path('reciprocal/<sample>/<run>', reciprocal.rlp),

    path('fragment/<fragment>/image', fragment.svg, name='fragment_svg'),
    path('crypt/', crypt.index),
]
