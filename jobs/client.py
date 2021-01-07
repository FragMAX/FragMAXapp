from typing import List
from itertools import count
from fragview.sites.plugin import BatchFile
from jobs import messages


def get_jobs():
    reply = messages.post_get_jobs_command()
    return reply.jobs


def cancel_jobs(job_ids):
    messages.post_cancel_jobs_command(job_ids)


def _assign_ids(jobs):
    jobs_id = {}

    for id, job in zip(count(), jobs):
        jobs_id[job] = f"{id}"

    return jobs_id


class JobsSet:
    def __init__(self, name):
        self._name = name
        self._jobs = []

    def add_job(self, batch_file: BatchFile, run_after: List[BatchFile] = []):
        self._jobs.append((batch_file, run_after))

    def submit(self):
        job_ids = _assign_ids([job for job, _ in self._jobs])

        jobs_list = []
        for job, run_after in self._jobs:
            job_dict = dict(
                name=job._name,
                program=job._filename,
                stdout=job._stdout,
                stderr=job._stderr,
                id=job_ids[job],
            )

            run_after_ids = [f"{job_ids[job]}" for job in run_after]
            if run_after_ids:
                job_dict["run_after"] = run_after_ids

            jobs_list.append(job_dict)

        messages.post_start_jobs_command(self._name, jobs_list)
