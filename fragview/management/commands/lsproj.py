from django.core.management.base import BaseCommand
from projects.database import db_session
from fragview.models import UserProject
from fragview.projects import get_project


class Command(BaseCommand):
    help = "list projects"

    @db_session
    def handle(self, *args, **options):
        for usr_proj in UserProject.objects.all():
            proj = get_project(usr_proj.id)
            print(f"{proj.id:3} {proj.protein:8} {proj.proposal} {proj.project_dir}")
