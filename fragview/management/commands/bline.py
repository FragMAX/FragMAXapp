from django.core.management.base import BaseCommand
from fragview.projects import get_dataset_metadata
from projects.database import db_session
from fragview.models import UserProject
from fragview.projects import get_project


class Command(BaseCommand):
    help = "set correct beamline for all datasets"

    @db_session
    def handle(self, *args, **options):
        #
        # for all datasets in all projects,
        # load 'beamline' value from dataset's metadata and
        # set that value into dataset's 'beamline' cell in the database
        #

        for usr_proj in UserProject.objects.all():
            project = get_project(usr_proj.id)

            print(f"setting beamline for {project.name}")

            for dset in project.get_datasets():
                beamline = get_dataset_metadata(
                    project,
                    project.get_dataset_raw_dir(dset),
                    dset.crystal.id,
                    dset.run,
                ).beamline

                print(f"for {dset.name} setting beamline '{beamline}'")

                dset.beamline = beamline
