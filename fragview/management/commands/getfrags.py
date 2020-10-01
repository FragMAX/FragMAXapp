from django.core.management.base import BaseCommand
from fragview.management.commands.utils import get_project


class Command(BaseCommand):
    help = "print the fragments library in CSV format"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)

    def handle(self, *args, **options):
        proj = get_project(options["project_id"])

        for frag in proj.library.fragment_set.all():
            print(f"{frag.name},{frag.smiles}")
