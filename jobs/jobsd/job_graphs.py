"""
handle building job dependencies graphs from
the flat lists
"""
from typing import List, Set
from jobs.messages import Job


class JobNode:
    def __init__(self, job, run_on):
        self.job = job
        self.run_on = run_on
        self.run_after = []

    def set_run_after(self, run_after):
        self.run_after = run_after

    def __repr__(self):
        return f"JobNode(name='{self.job.name}')"


def to_linked_job_nodes(jobs_list: List[dict]) -> Set[JobNode]:
    """
    convert the flat list of jobs list, with ID references to a 'run_after' dependencies
    to a list of JobNode, with dependency linked to JobNode instances
    """
    jobs_by_id = {}

    for job_desc in jobs_list:
        run_after = job_desc.get("run_after", [])

        jobs_by_id[job_desc["id"]] = (
            JobNode(
                Job(
                    None,
                    job_desc["name"],
                    job_desc["program"],
                    job_desc["stdout"],
                    job_desc["stderr"],
                ),
                job_desc["run_on"],
            ),
            run_after,
        )

    jobs = set()

    for id, (job, run_after) in jobs_by_id.items():
        run_after_jobs = [jobs_by_id[jid][0] for jid in run_after]
        job.set_run_after(run_after_jobs)

        jobs.add(job)

    return jobs


def get_root_jobs(jobs_nodes: Set[JobNode]) -> Set[JobNode]:
    root_jobs = jobs_nodes.copy()

    for job in jobs_nodes:
        for run_after_job in job.run_after:
            root_jobs.remove(run_after_job)

    return root_jobs
