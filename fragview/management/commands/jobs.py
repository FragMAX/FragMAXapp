from typing import Iterable
from django.core.management.base import BaseCommand
from fragview.models import UserProject
from fragview.projects import get_project
from projects.database import db_session


def _get_project_ids() -> Iterable[str]:
    for usr_proj in UserProject.objects.all():
        yield str(usr_proj.id)


@db_session
def _print_jobs(project_id: str):
    project = get_project(project_id)
    cntr = 0

    for job in project.get_running_jobs():
        print(f"{project_id: >4} {project.name: >20} {job.id: >6} {job.description}")
        cntr += 1

    return cntr


class Command(BaseCommand):
    help = "show running jobs"

    def handle(self, *args, **options):
        cntr = 0

        for project_id in _get_project_ids():
            cntr += _print_jobs(project_id)

        print(f"{cntr} running job(s)")
