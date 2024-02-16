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
    # data analyse views
    path("analysis/process", analysis.process),
    path("analysis/refine", analysis.refine),
    path("analysis/ligfit", analysis.ligfit),
    path("analysis/pandda", analysis.pandda),
    path("datasets/process", datasets.process),
    path("datasets/refine", datasets.refine),
    path("datasets/ligfit", datasets.ligfit),
    path("datasets/pandda", datasets.pandda),
    path("hpc/kill/", hpc.kill),
    path("jobs/status", hpc.status, name="hpcstatus"),
    path("jobs/history", hpc.jobhistory, name="jobhistory"),
    path(
        "diffraction/<dataset_id>/<angle>",
        diffraction.image,
        name="diffraction_image",
    ),
    # MTZs
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
