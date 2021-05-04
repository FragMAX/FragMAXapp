from django.core.management.base import BaseCommand, CommandError
from fragview.management.commands.utils import get_project
from fragview.scraper import PROC_TOOLS, REFINE_TOOLS, LIGFIT_TOOLS
from fragview.status import (
    update_proc_tool_status,
    update_refine_tool_status,
    update_ligfit_tool_status,
)
from projects.database import db_session


class Command(BaseCommand):
    help = "update processing results of a tool for a dataset"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)
        parser.add_argument("tool", type=str)
        parser.add_argument("dataset_id", type=str)

    @db_session
    def handle(self, *args, **options):
        project = get_project(options["project_id"])
        tool = options["tool"]
        dataset_id = options["dataset_id"]

        # look-up data set object
        dataset = project.get_dataset(dataset_id)
        if dataset is None:
            raise CommandError(f"no dataset with ID '{dataset_id}' exist")

        if tool in PROC_TOOLS:
            update_proc_tool_status(project, tool, dataset)
            return

        if tool in REFINE_TOOLS:
            update_refine_tool_status(project, tool, dataset)
            return

        if tool in LIGFIT_TOOLS:
            update_ligfit_tool_status(project, tool, dataset)
            return

        # unexpected tool specified
        raise CommandError(f"unknown tool '{tool}'")
