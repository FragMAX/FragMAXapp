from django.core.management.base import BaseCommand
from fragview.management.commands.utils import get_project
from fragview.scraper import (
    scrape_processing_outcome,
    scrape_refine_results,
    PROC_TOOLS,
)
from fragview.dsets import update_dataset_status
from fragview.results import update_dataset_results
from worker import dist_lock


def _update_tool_status(project, tool, dataset):
    status = scrape_processing_outcome(project, tool, dataset)

    lock_id = f"update_tool_status|{project.id}"
    with dist_lock.acquire(lock_id):
        update_dataset_status(project, tool, dataset, status)


def _update_refine_results(project, tool, dataset):
    if tool in PROC_TOOLS:
        # data processing tools (xds, et all)
        # don't generate 'structure refine' results,
        # nothing to do here
        return

    results = scrape_refine_results(project, tool, dataset)
    lock_id = f"update_tool_results|{project.id}"
    with dist_lock.acquire(lock_id):
        update_dataset_results(project, dataset, tool, results)


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

        _update_tool_status(project, tool, dataset)
        _update_refine_results(project, tool, dataset)
