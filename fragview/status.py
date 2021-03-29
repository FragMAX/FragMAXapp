from fragview.projects import (
    project_script,
    project_scripts_dir,
    project_syslog_path,
    project_datasets,
    parse_dataset_name,
    UPDATE_STATUS_SCRIPT,
)
from fragview.scraper import (
    scrape_processing_outcome,
    scrape_refine_results,
)
from fragview.sites import SITE
from fragview.sites.plugin import Pipeline
from fragview.dsets import get_datasets
from fragview.dsets import update_dataset_status
from fragview.results import update_dataset_results
from jobs.client import JobsSet
from fragview import dist_lock

AUTOPROC_TOOLS = {
    Pipeline.EDNA_PROC: "edna",
    Pipeline.AUTO_PROC: "autoproc",
}


def update_tool_status(project, tool, dataset):
    status = scrape_processing_outcome(project, tool, dataset)

    lock_id = f"update_tool_status|{project.id}"
    with dist_lock.acquire(lock_id):
        update_dataset_status(project, tool, dataset, status)


def update_refine_results(project, tool, dataset):
    results = scrape_refine_results(project, tool, dataset)

    lock_id = f"update_tool_results|{project.id}"
    with dist_lock.acquire(lock_id):
        update_dataset_results(project, dataset, tool, results)


def _supported_autoproc_tools():
    supported_tools = set()
    for pipeline in SITE.get_supported_pipelines():
        tool = AUTOPROC_TOOLS.get(pipeline)
        if tool is not None:
            supported_tools.add(tool)

    return supported_tools


def set_imported_autoproc_status(project):
    tools = _supported_autoproc_tools()

    if not tools:
        # this site does not support importing
        # any auto-processed data, nothing to do here
        return

    for dataset in get_datasets(project):
        dset_name = f"{dataset.image_prefix}_{dataset.run}"
        for tool in tools:
            print(f"scrape {dset_name} for {tool}")
            # TODO: re-structure code so we don't rewrite
            # TODO: allstatus.csv for each dataset/tool combination,
            # TODO: which is, ehhh, somewhat un-optimal
            update_tool_status(project, tool, dset_name)


def run_update_status(proj):
    jobs = JobsSet("update_status")
    hpc = SITE.get_hpc_runner()

    #
    # generate the wrapper batch script
    #
    batch = hpc.new_batch_file(
        "init_project_status",
        project_script(proj, "update_status.sh"),
        project_syslog_path(proj, "init_project_status_%j.out"),
        project_syslog_path(proj, "init_project_status_%j.err"),
    )

    batch.load_python_env()
    batch.add_command(f"cd {project_scripts_dir(proj)}")

    for dset in project_datasets(proj):
        # for each dataset, run the update status script
        dataset, run = parse_dataset_name(dset)

        batch.add_command(
            f"python3 ./{UPDATE_STATUS_SCRIPT} {proj.data_path()} {dataset} {run}"
        )

    batch.save()
    jobs.add_job(batch)
    jobs.submit()
