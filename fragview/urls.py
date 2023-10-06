from django.urls import path, re_path
from fragview.views import (
    projects,
    datasets,
    details,
    snapshot,
    hpc,
    results,
    density,
    analysis,
    pandda,
    pdbs,
    diffraction,
    eldensity,
    libraries,
    crystals,
    fragment,
    result_pdbs,
    download,
    dataset_info,
    logs,
    commit,
    fragments,
)

urlpatterns = [
    # use 'project summary' view as the landing page
    path("", projects.project_summary, name="project_summary"),
    path("datasets/", datasets.show_all, name="datasets"),
    path("dataset_info/<dataset_id>", dataset_info.show, name="dataset_info"),
    path("dataset/<dataset_id>/snapshot/<snapshot_index>", snapshot.show),
    path("results/", results.show, name="results"),
    path("results/isa", results.isa),
    path("results/rfactor", results.rfactor),
    path("results/resolution", results.resolution),
    path("results/cellparams", results.cellparams),
    path("density/<result_id>", density.show, name="density"),
    path("dual_density/<result_id>", density.compare_poses, name="dual_density"),
    path("pandda_density/", density.pandda, name="pandda_density"),
    path(
        "pandda_densityC/<method>/<dataset_name>/<site_idx>/<event_idx>",
        density.pandda_consensus,
        name="pandda_densityC",
    ),
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
    path("pandda/process", pandda.process),
    # pandda cluster dendrogram images
    path("pandda/cluster/<method>/<cluster>/image", pandda.cluster_image),
    # pandda HTML report for a specific analysis run
    path("pandda/analysis/report/<method>/<date>", pandda.analysis_report),
    path("pandda/analysis/delete/<method>/<date>", pandda.delete_report),
    # fragment libraries views
    path("libraries/show", libraries.show, name="libraries"),
    path("libraries/new", libraries.new, name="libraries"),
    path("libraries/<library_id>/json", libraries.as_json, name="libraries"),
    path("libraries/<library_id>/csv", libraries.as_csv, name="libraries"),
    path("libraries/import", libraries.import_new),
    # project fragments view
    path("fragments/show", fragments.show, name="library_view"),
    # crystals management views
    path("crystals", crystals.show),
    path("crystals/new", crystals.new),
    path("crystals/import", crystals.import_csv),
    # project management views
    path("projects/", projects.show, name="manage_projects"),
    path("project/new", projects.new, name="new_project"),
    path("project/<int:id>", projects.delete),
    path("project/current/<int:id>/", projects.set_current),
    # project details (for PDB deposition) view
    path("project/details/ui", details.ui),
    path("project/details", details.details),
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
    path("pdbs/ligand/<result_id>", result_pdbs.ligand),
    path("pdbs/pandda/fitted/<dataset>/<method>", result_pdbs.pandda_fitted),
    path("pdbs/pandda/input/<dataset>/<method>", result_pdbs.pandda_input),
    # data analyse views
    path("analysis/process", analysis.process),
    path("analysis/refine", analysis.refine),
    path("analysis/ligfit", analysis.ligfit),
    path("analysis/pandda", analysis.pandda),
    path("datasets/process", datasets.process),
    path("datasets/refine", datasets.refine),
    path("datasets/ligfit", datasets.ligfit),
    path("hpc/kill/", hpc.kill),
    path("jobs/status", hpc.status, name="hpcstatus"),
    path("jobs/history", hpc.jobhistory, name="jobhistory"),
    path(
        "diffraction/<dataset_id>/<angle>",
        diffraction.image,
        name="diffraction_image",
    ),
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
    path("fragment/<fragment_id>/image", fragment.svg, name="fragment_svg"),
    # dataset processing logs
    re_path(r"logs/dset/(?P<dataset_id>\d+)/(?P<log_file>.*)$", logs.show_dset),
    re_path(
        r"logs/dset/download/(?P<dataset_id>\d+)/(?P<log_file>.*)$", logs.download_dset
    ),
    re_path(
        r"logs/dset/htmldata/(?P<dataset_id>\d+)/(?P<data_file>.*)$", logs.htmldata_dset
    ),
    # jobs logs
    re_path("logs/job/show/(?P<log_file>.*)$", logs.show_job),
    re_path("logs/job/download/(?P<log_file>.*)$", logs.download_job),
    # running commit, for tracking and troubleshooting
    path("commit", commit.show, name="commit"),
]
