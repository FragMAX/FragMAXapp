from sys import stdin, stdout
from django.core.management.base import BaseCommand
from fragview.management.commands.utils import get_project
from fragview.views import projects
from projects.database import db_session


def is_that_a_yes():
    for line in stdin:
        line = line.strip().lower()

        if line in ["y", "yes"]:
            return True

        if line in ["n", "no"]:
            return False

        print("Please type 'yes' or 'no'.")


class Command(BaseCommand):
    help = "remove project"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)

    @db_session
    def handle(self, *args, **options):
        proj = get_project(options["project_id"])

        question = f"Remove project '{proj.name}' ? "
        stdout.write(question)
        stdout.flush()

        if is_that_a_yes():
            projects.delete(None, proj.id)
            print(f"Project {proj.name} deleted.")
