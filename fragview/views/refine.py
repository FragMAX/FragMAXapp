import time
from pathlib import Path
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from fragview import versions
from fragview.views import crypt_shell
from fragview.views.utils import start_thread
from fragview.projects import (
    current_project,
    project_script,
    project_log_path,
    Project,
)
from fragview.filters import get_refine_datasets
from fragview.pipeline_commands import (
    get_dimple_command,
    get_fspipeline_commands,
)
from fragview.forms import RefineForm
from fragview.sites import SITE
from fragview.sites.plugin import Duration, DataSize
from fragview.views.update_jobs import add_update_job
from fragview.scraper import dials, xds, xdsapp, edna, autoproc
from jobs.client import JobsSet
from projects.database import db_session


HPC_MODULES = ["gopresto", versions.BUSTER_MOD, versions.PHENIX_MOD]


def datasets(request):
    project = current_project(request)

    form = RefineForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(f"invalid refinement arguments {form.errors}")

    pdb = project.get_pdb(id=form.pdb_model)
    pdb_file = project.get_pdb_file(pdb)

    if form.use_dimple:
        cmd, cpus = get_dimple_command("input.mtz", form.custom_dimple)
        start_thread(
            launch_refine_jobs,
            project,
            form.datasets_filter,
            pdb_file,
            form.space_group,
            form.run_aimless,
            "dimple",
            [cmd],
            cpus,
        )

    if form.use_fspipeline:
        cmds, cpus = get_fspipeline_commands(pdb_file, form.custom_fspipe)
        start_thread(
            launch_refine_jobs,
            project,
            form.datasets_filter,
            pdb_file,
            form.space_group,
            form.run_aimless,
            "fspipeline",
            cmds,
            cpus,
        )

    return render(request, "jobs_submitted.html")


@db_session
def launch_refine_jobs(
    project: Project,
    filters,
    pdb_file,
    space_group,
    run_aimless,
    refine_tool,
    refine_tool_commands,
    cpus,
):
    epoch = round(time.time())
    jobs = JobsSet("Refine")
    hpc = SITE.get_hpc_runner()

    for dset in get_refine_datasets(project, filters, refine_tool):
        for tool, input_mtz in _find_input_mtzs(project, dset):
            batch = hpc.new_batch_file(
                f"refine {tool} {dset.name}",
                project_script(project, f"refine_{tool}_{refine_tool}_{dset.name}.sh"),
                project_log_path(
                    project, f"refine_{tool}_{dset.name}_{epoch}_%j_out.txt"
                ),
                project_log_path(
                    project, f"refine_{tool}_{dset.name}_{epoch}_%j_err.txt"
                ),
                cpus,
            )
            batch.set_options(
                time=Duration(hours=12),
                nodes=1,
                mem_per_cpu=DataSize(gigabyte=5),
            )

            batch.add_commands(crypt_shell.crypt_cmd(project))

            batch.assign_variable("WORK_DIR", "`mktemp -d`")
            batch.add_commands(
                "cd $WORK_DIR",
                crypt_shell.fetch_file(project, pdb_file, "model.pdb"),
                crypt_shell.fetch_file(project, input_mtz, "input.mtz"),
            )

            # TODO: load tool specific modules?
            batch.load_modules(HPC_MODULES)

            if run_aimless:
                batch.add_commands(_aimless_cmd(space_group.short_name, "input.mtz"))

            results_dir = Path(project.get_dataset_results_dir(dset), tool)

            batch.add_commands(
                *refine_tool_commands,
                _upload_result_cmd(project, results_dir),
                "cd",
                "rm -rf $WORK_DIR",
            )

            batch.save()
            jobs.add_job(batch)

            add_update_job(jobs, hpc, project, refine_tool, dset, batch)

    jobs.submit()


def _find_input_mtzs(project: Project, dataset):
    if dataset.processed_successfully("dials"):
        yield "dials", dials.get_result_mtz(project, dataset)

    if dataset.processed_successfully("xds"):
        yield "xds", xds.get_result_mtz(project, dataset)

    if dataset.processed_successfully("xdsapp"):
        yield "xdsapp", xdsapp.get_result_mtz(project, dataset)

    if dataset.processed_successfully("autoproc"):
        yield "autoproc", autoproc.get_result_mtz(project, dataset)

    if dataset.processed_successfully("edna"):
        yield "edna", edna.get_result_mtz(project, dataset)


def _aimless_cmd(spacegroup, dstmtz):
    return (
        f"echo 'choose spacegroup {spacegroup}' | pointless HKLIN {dstmtz} HKLOUT {dstmtz} | tee "
        f"pointless.log ; sleep 0.1 ; echo 'START' | aimless HKLIN "
        f"{dstmtz} HKLOUT {dstmtz} | tee aimless.log"
    )


def _upload_result_cmd(proj, res_dir):
    return (
        f"# upload results\n"
        + f"rm $WORK_DIR/model.pdb\n"
        + f"{crypt_shell.upload_dir(proj, '$WORK_DIR', res_dir)}"
    )
