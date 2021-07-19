from django.core.management.base import BaseCommand
from fragview.management.commands.utils import get_project
from fragview.projects import Project
from projects.database import db_session
from fragview.scraper import PROC_TOOLS, REFINE_TOOLS, LIGFIT_TOOLS
from fragview.status import (
    update_proc_tool_status,
    update_refine_tool_status,
    update_ligfit_tool_status,
)


def _resync_dataset(project: Project, dataset):
    for tool in PROC_TOOLS:
        update_proc_tool_status(project, tool, dataset)

    for tool in REFINE_TOOLS:
        update_refine_tool_status(project, tool, dataset)

    for tool in LIGFIT_TOOLS:
        update_ligfit_tool_status(project, tool, dataset)


class Command(BaseCommand):
    help = "resync processing results for all datasets in a project"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)

    @db_session
    def handle(self, *args, **options):
        project = get_project(options["project_id"])

        for dataset in project.get_datasets():
            print(f"update results for {dataset.name}")
            _resync_dataset(project, dataset)
