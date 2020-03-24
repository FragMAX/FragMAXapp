from django.core.management.base import BaseCommand, CommandError
from fragview.models import Project
from fragview import tokens


class Command(BaseCommand):
    help = "generate a crypto access token"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)

    def handle(self, *args, **options):
        proj_id = options["project_id"]
        try:
            proj = Project.get(proj_id)
        except Project.DoesNotExist:
            raise CommandError(f"no project with id {proj_id} exist")

        if not proj.encrypted:
            raise CommandError("encryption for project disabled, can't generate tokens")

        tok = tokens.get_valid_token(proj)
        print(tok.as_base64())
