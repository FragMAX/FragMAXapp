from django.urls import path, re_path
from fragview.views import (
    projects,
    datasets,
    snapshot,
    hpc,
    results,
    density,
    misc,
    analysis,
    pandda,
    reciprocal,
    soaking,
    pdbs,
    pipedream,
    refine,
    process,
    ligfit,
    diffraction,
    eldensity,
    libraries,
    fragment,
    crypt,
    result_pdbs,
    encryption,
    download,
    dataset_info,
    logs,
    commit,
    fragments,
)

urlpatterns = [
    # use 'project summary' view as the landing page
    path("", projects.project_summary, name="project_summary"),
    path("soaking_plan/", soaking.soaking_plan, name="soaking_plan"),
    path("datasets/", datasets.show_all, name="datasets"),
    path("dataset_info/<dataset_id>", dataset_info.show, name="dataset_info"),
    path("dataset/<dataset_id>/snapshot/<snapshot_index>", snapshot.show),
    path("results/", results.show, name="results"),
    path("results/isa", results.isa),
    path("results/rfactor", results.rfactor),
    path("results/resolution", results.resolution),
    path("results/cellparams", results.cellparams),
    path("density/<result_id>", density.show, name="density"),
    path("dual_density/", density.compare_poses, name="dual_density"),
    path("pipedream_density/", density.show_pipedream, name="pipedream_density"),
    path("pandda_density/", density.pandda, name="pandda_density"),
    path("pandda_densityC/", density.pandda_consensus, name="pandda_densityC"),
    path(
        "pandda_densityA/<method>/<dataset_name>",
        density.pandda_analyse,
        name="pandda_densityA",
    ),
    # show pandda analysis reports for latest processed methods
    path("pandda_analyse/", pandda.analyse, name="pandda_analyse"),
    # show pandda analysis reports for specified method
    path("pandda_analyse/<method>", pandda.analyse, name="pandda_analyse"),
    path("pandda_inspect/", pandda.inspect, name="pandda_inspect"),
    path("submit_pandda/", pandda.submit, name="submit_pandda"),
    # pandda cluster dendrogram images
    path("pandda/cluster/<method>/<cluster>/image", pandda.cluster_image),
    # pandda HTML report for a specific analysis run
    path("pandda/analysis/report/<method>/<date>", pandda.analysis_report),
    path("ugly/", misc.ugly, name="ugly"),
    path(
        "reciprocal_lattice/<sample>/<run>", reciprocal.show, name="reciprocal_lattice"
    ),
    path("project_details/", misc.project_details, name="project_details"),
    path("libraries/show", libraries.show, name="libraries"),
    path("libraries/<library_id>/json", libraries.as_json, name="libraries"),
    path("libraries/<library_id>/csv", libraries.as_csv, name="libraries"),
    path("fragments/show", fragments.show, name="library_view"),
    path("download_options/", misc.download_options, name="download_options"),
    # project management views
    path("projects/", projects.show, name="manage_projects"),
    path("project/<int:id>/", projects.edit),
    path("project/new", projects.new, name="new_project"),
    path("project/update_library", projects.update_library, name="update_library"),
    path("project/current/<int:id>/", projects.set_current),
    # encryption key management views
    path("encryption/", encryption.show, name="encryption"),
    path("encryption/key/", encryption.download_key),
    path("encryption/key/upload/", encryption.upload_key),
    path("encryption/key/forget/", encryption.forget_key),
    # PDBs management views
    path("pdbs/", pdbs.list, name="manage_pdbs"),
    path("pdb/<int:id>", pdbs.edit),
    path("pdb/add", pdbs.add),
    path("pdb/new", pdbs.new),
    path("pdb/get/<int:id>", pdbs.get),
    # download views
    path("download/", download.page),
    path("download/pandda", download.pandda),
    # generated PDB access views
    path("pdbs/refined/<result_id>", result_pdbs.refined),
    # TODO: remove url below?
    path("pdbs/final/<dataset>/<process>/<refine>", result_pdbs.final),
    path("pdbs/ligand/<result_id>", result_pdbs.ligand),
    path("pdbs/pandda/fitted/<dataset>/<method>", result_pdbs.pandda_fitted),
    path("pdbs/pandda/input/<dataset>/<method>", result_pdbs.pandda_input),
    path("data_analysis/", analysis.processing_form, name="data_analysis"),
    path("pipedream/", pipedream.processing_form, name="pipedream"),
    path("submit_pipedream/", pipedream.submit, name="submit_pipedream"),
    path("hpc/kill/", hpc.kill),
    path("jobs/status", hpc.status, name="hpcstatus"),
    path("jobs/history", hpc.jobhistory, name="jobhistory"),
    path("dataproc_datasets/", process.datasets, name="dataproc_datasets"),
    path("refine_datasets/", refine.datasets, name="refine_datasets"),
    path("ligfit_datasets/", ligfit.datasets, name="ligfit_datasets"),
    path(
        "diffraction/<dataset_id>/<angle>", diffraction.image, name="diffraction_image",
    ),
    path("pipedream_ccp4_map/<sample>/<process>/<type>", eldensity.pipedream_map),
    # pandda generated density maps
    path("density_map/pandda/<dataset>/<method>/zmap", eldensity.pandda_consensus_zmap),
    path("density_map/pandda/<dataset>/<method>/bdc", eldensity.pandda_bdc),
    path("density_map/pandda/<dataset>/<method>/average", eldensity.pandda_average),
    path("density_map/pandda/<dataset>/<method>/input", eldensity.pandda_input),
    # MTZs, note: must be listed after 'density_map/pandda' URLs
    path(
        "density_map/refined/<result_id>/<type>",
        eldensity.refined_map,
        name="density_map",
    ),
    path("reciprocal/<sample>/<run>", reciprocal.rlp),
    path("fragment/<fragment_id>/image", fragment.svg, name="fragment_svg"),
    path("crypt/", crypt.index),
    # tools specific logs
    path("logs/autoproc/show/<dataset>/<log_file>", logs.show_autoproc),
    re_path("logs/imported/htmldata/(?P<data_file>.*)$", logs.imported_htmldata),
    # generic logs
    re_path("logs/show/(?P<log_file>.*)$", logs.show),
    re_path("logs/download/(?P<log_file>.*)$", logs.download),
    re_path("logs/htmldata/(?P<data_file>.*)$", logs.htmldata),
    # running commit, for tracking and trouble shooting
    path("commit", commit.show, name="commit"),
]
