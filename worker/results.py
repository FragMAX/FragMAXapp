from os import path
from glob import glob
import celery
import subprocess
from celery.utils.log import get_task_logger
from worker import dist_lock
from fragview.models import Project
from fragview.sites import SITE
from fragview.projects import (
    project_script,
    project_syslog_path,
    get_update_results_command,
)
from jobs.client import JobsSet

logger = get_task_logger(__name__)


def _lock_id(proj):
    return f"resync_results|{proj.id}"


def resync_active(proj):
    return dist_lock.is_acquired(_lock_id(proj))


@celery.task
def resync_results(proj_id):
    try:
        proj = Project.get(proj_id)
    except Project.DoesNotExist:
        logger.warning(f"warning: no project with ID {proj_id}, will to resync results")
        return

    with dist_lock.acquire(_lock_id(proj)):
        logger.info(
            f"re-sync results file for project {proj.protein}-{proj.library.name} ({proj.id})"
        )
        _generate_results_file(proj)


def _generate_results_file(proj):
    resultsList = glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*")
    resultscsv = f"{proj.data_path()}/fragmax/process/{proj.protein}/results.csv"
    if not path.exists(resultscsv):
        subprocess.call(["touch", resultscsv])

    jobs = JobsSet("re-sync results")
    batch = SITE.get_hpc_runner().new_batch_file(
        f"re-synch results",
        project_script(proj, "resync_results.sh"),
        project_syslog_path(proj, "resync_results_%j.out"),
        project_syslog_path(proj, "resync_results_%j.err"),
    )
    batch.load_python_env()
    for result in resultsList:
        dataset, run = path.basename(result).split("_")

        batch.add_command(get_update_results_command(proj, dataset, run))

    batch.save()
    jobs.add_job(batch)
    jobs.submit()
