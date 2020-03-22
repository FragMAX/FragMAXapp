from django.core.management.base import BaseCommand, CommandError
from fragview.encryption import generate_token
from fragview.models import Project, AccessToken


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

        tok = AccessToken.add_token(proj, generate_token())
        print(tok.as_base64())
