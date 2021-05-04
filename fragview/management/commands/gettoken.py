from django.core.management.base import BaseCommand, CommandError
from fragview import tokens
from fragview.management.commands.utils import get_project
from projects.database import db_session


class Command(BaseCommand):
    help = "generate a crypto access token"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)

    @db_session
    def handle(self, *args, **options):
        project = get_project(options["project_id"])

        if not project.encrypted:
            raise CommandError("encryption for project disabled, can't generate tokens")

        tok = tokens.get_valid_token(project)
        print(tok.as_base64())
