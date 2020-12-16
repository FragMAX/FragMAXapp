from fragview.projects import (
    project_script,
    project_scripts_dir,
    project_syslog_path,
    project_datasets,
    UPDATE_STATUS_SCRIPT,
)
from fragview.sites import SITE
from jobs.client import JobsSet


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
        dataset, run = dset.rsplit("_")
        batch.add_command(
            f"python3 ./{UPDATE_STATUS_SCRIPT} {proj.data_path()} {dataset} {run}"
        )

    batch.save()
    jobs.add_job(batch)
    jobs.submit()
