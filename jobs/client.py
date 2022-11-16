from typing import List, Tuple
from enum import Enum
from pony import orm
from fragview.projects import Project, get_project
from fragview.sites.plugin import BatchFile
from projects.database import db_session
from jobs import messages


def cancel_jobs(project_id, job_ids: List[str]):
    messages.post_cancel_jobs_command(str(project_id), job_ids)


def _expand_logs_path_template(jobs_set):
    """
    expand log path template for all jobs in specified 'jobs set'

    Note, this function assumes that:
      1) all the jobs in 'jobs set' are committed to DB
      2) an active DB session exist
    """

    def _expand_template(template: str, job_id):
        """
        emulate slurms's '%j' template,
        i.e. replace it with job ID
        """
        return template.replace("%j", f"{job_id}")

    for job in jobs_set.jobs:
        job.stdout = _expand_template(job.stdout, job.id)
        job.stderr = _expand_template(job.stderr, job.id)

    orm.commit()


class JobsSet:
    class Destination(Enum):
        HPC = "hpc"
        LOCAL = "local"

    def __init__(self, project: Project, name: str):
        self._project_id = str(project.id)
        self._name = name
        self._jobs: List[Tuple] = []

    def add_job(
        self,
        batch_file: BatchFile,
        arguments: List[str] = [],
        run_after: List[BatchFile] = [],
        run_on: Destination = Destination.HPC,
    ):
        self._jobs.append((batch_file, arguments, run_after, run_on))

    def _write_to_db(self):
        batch2job = {}

        db = get_project(self._project_id).db
        jobs_set = db.JobsSet(description=self._name)

        for batch_file, arguments, run_after, run_on in self._jobs:
            args = dict(
                jobs_set=jobs_set,
                description=batch_file._name,
                program=batch_file._filename,
                stdout=batch_file._stdout,
                stderr=batch_file._stderr,
                run_on=run_on.value,
            )

            if batch_file._cpus:
                args["cpus"] = batch_file._cpus

            job = db.Job(**args)
            job.set_arguments(arguments)

            batch2job[batch_file] = job

        # store 'run_after' dependencies in the database
        for batch_file, _, run_after, _ in self._jobs:
            job = batch2job[batch_file]
            job.previous_jobs = [batch2job[dep] for dep in run_after]

        orm.commit()

        return jobs_set

    @db_session
    def submit(self):
        jobs_set = self._write_to_db()
        _expand_logs_path_template(jobs_set)

        messages.post_start_jobs_set_command(self._project_id, jobs_set.id)
