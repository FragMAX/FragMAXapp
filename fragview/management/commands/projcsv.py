from django.core.management.base import BaseCommand
from fragview.management.commands.utils import get_project
from fragview.views.utils import get_crystals_fragment
from projects.database import db_session


class Command(BaseCommand):
    help = "generate project CSV file"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)

    @db_session
    def handle(self, *args, **options):
        def _get_frag_info(crystal):
            if crystal.is_apo():
                return "", ""

            frag = get_crystals_fragment(crystal)
            return frag.library.name, frag.code

        project = get_project(options["project_id"])

        print("SampleID,FragmentLibrary,FragmentCode")

        for crystal in project.get_crystals():
            library, fragment = _get_frag_info(crystal)
            print(f"{crystal.id},{library},{fragment}")
