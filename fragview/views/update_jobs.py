from fragview.projects import project_syslog_path
from jobs.client import JobsSet


def add_update_job(jobs_set: JobsSet, hpc, project, tool, dataset, dataset_batch):
    batch = hpc.new_batch_file(
        f"update results for {dataset}",
        "./manage.py",
        project_syslog_path(project, "update_dataset_results-%j.stdout"),
        project_syslog_path(project, "update_dataset_results-%j.stderr"),
    )

    jobs_set.add_job(
        batch,
        ["update", f"{project.id}", tool, dataset],
        run_after=[dataset_batch],
        run_on=JobsSet.Destination.LOCAL,
    )

    return batch
