from os import path
from glob import glob
import celery
import subprocess
from celery.utils.log import get_task_logger
from worker import dist_lock
from fragview.models import Project
from fragview import hpc

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
        logger.info(f"re-sync results file for project {proj.protein}-{proj.library.name} ({proj.id})")
        _generate_results_file(proj)


def _generate_results_file(proj):
    resultsList = glob(f"{proj.data_path()}/fragmax/results/{proj.protein}*")
    resultscsv = f"{proj.data_path()}/fragmax/process/{proj.protein}/results.csv"
    if not path.exists(resultscsv):
        subprocess.call(['touch', resultscsv])
    script = f"{proj.data_path()}/fragmax/scripts/update_results.sh"
    with open(f"{proj.data_path()}/fragmax/scripts/update_results.sh", "w") as writeFile:
        writeFile.write("#!/bin/bash\n")
        writeFile.write("#!/bin/bash\n")
        writeFile.write("module purge\n")
        writeFile.write("module load GCC/7.3.0-2.30  OpenMPI/3.1.1 Python/3.7.0\n")
        for result in resultsList:
            writeFile.write(f"python3 {proj.data_path()}/fragmax/scripts/update_results.py {path.basename(result)} "
                            f"{proj.proposal}/{proj.shift}\n")
    hpc.run_sbatch(script)
