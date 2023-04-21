from datetime import datetime
from projects.database import get_project_db, db_session
import conf


class JobNode:
    def __init__(
        self,
        project_id: str,
        db_job_id: str,
        description,
        program,
        arguments,
        stdout,
        stderr,
        cpus,
        run_on,
    ):
        self.description = description
        self.program = program
        self.arguments = arguments
        self.stdout = stdout
        self.stderr = stderr
        self.cpus = cpus
        self.run_on = run_on
        self.previous_jobs: list[JobNode] = []

        # DB reference
        self.project_id = project_id
        self.db_job_id = db_job_id


def _get_db(project_id):
    return get_project_db(conf.PROJECTS_DB_DIR, project_id)


def _get_db_job(job_node: JobNode):
    db = _get_db(job_node.project_id)
    return db.Job.get(id=job_node.db_job_id)


@db_session
def mark_job_started(job_node: JobNode):
    job = _get_db_job(job_node)
    job.started = datetime.now()


@db_session
def mark_job_finished(job_node: JobNode):
    job = _get_db_job(job_node)
    job.finished = datetime.now()


@db_session
def get_job_nodes(project_id, jobs_set_id) -> list[JobNode]:
    """
    read from database specified jobs set and return
    all job as JobNode objects
    """
    nodes = []
    job2node = {}
    db = _get_db(project_id)
    jobs_set = db.JobsSet.get(id=jobs_set_id)

    for job in jobs_set.jobs:
        node = JobNode(
            str(project_id),
            str(job.id),
            job.description,
            job.program,
            job.get_arguments(),
            job.stdout,
            job.stderr,
            job.cpus,
            job.run_on,
        )
        nodes.append(node)
        job2node[job] = node

    # reconstruct 'previous jobs' dependencies for job nodes
    for job in jobs_set.jobs:
        node = job2node[job]
        for prev_job in job.previous_jobs:
            node.previous_jobs.append(job2node[prev_job])

    return nodes


def get_root_nodes(job_nodes: list[JobNode]) -> set[JobNode]:
    roots = set(job_nodes)

    for node in job_nodes:
        for prev_node in node.previous_jobs:
            roots.remove(prev_node)

    return roots
