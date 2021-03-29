from django.core.management.base import BaseCommand
from fragview.management.commands.utils import get_project
from fragview.scraper import REFINE_TOOLS
from fragview.status import update_tool_status, update_refine_results


class Command(BaseCommand):
    help = "update processing results of a tool for a dataset"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)
        parser.add_argument("tool", type=str)
        parser.add_argument("dataset", type=str)

    def handle(self, *args, **options):
        project = get_project(options["project_id"])
        tool = options["tool"]
        dataset = options["dataset"]

        update_tool_status(project, tool, dataset)
        if tool in REFINE_TOOLS:
            update_refine_results(project, tool, dataset)
