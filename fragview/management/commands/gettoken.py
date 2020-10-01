from django.core.management.base import BaseCommand, CommandError
from fragview import tokens
from fragview.management.commands.utils import get_project


class Command(BaseCommand):
    help = "generate a crypto access token"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)

    def handle(self, *args, **options):
        proj = get_project(options["project_id"])

        if not proj.encrypted:
            raise CommandError("encryption for project disabled, can't generate tokens")

        tok = tokens.get_valid_token(proj)
        print(tok.as_base64())
