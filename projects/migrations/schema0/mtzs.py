from pony.orm import db_session
from projects.migrations import ProjectDesc
from fragview.projects import get_project, Project
from fragview.scraper import PROC_TOOLS
from fragview.status import update_proc_tool_status


def _resync_dataset(project: Project, dataset):
    print(f"re-syncing dataset: {dataset.name}")

    for result in dataset.result:
        if result.result == "ok" and result.tool in PROC_TOOLS:
            update_proc_tool_status(project, result.tool, dataset)


@db_session
def migrate_process_result_table(project_desc: ProjectDesc):
    project = get_project(project_desc.project_id)

    # re-synch all datasets, so that we overwrite
    # space group and unit cell values loaded from MTZ file,
    # rather then old values scraped from tool specific logs
    for dataset in project.get_datasets():
        _resync_dataset(project, dataset)
