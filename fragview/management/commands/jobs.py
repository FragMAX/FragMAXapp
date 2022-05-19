from django.core.management.base import BaseCommand
from jobs import client


class Command(BaseCommand):
    help = "show running jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "-p", "--project-id", default=None, help="Show jobs for specified project."
        )

    def handle(self, *args, **options):
        project_id = options["project_id"]

        jobs = client.get_jobs(project_id)
        for job in jobs:
            print(f"id {job.id} proj {job.project_id} '{job.name}' {job.start_time}")

        print(f"    {len(jobs)} running job(s)")
