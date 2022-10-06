from typing import Iterable
from pathlib import Path
from functools import reduce
from django.core.management.base import BaseCommand, CommandError
from fragview.management.commands.utils import get_project
from projects.database import db_session


def _gigabytes(bytes_num) -> str:
    gbytes = bytes_num / 10**9
    return f"{gbytes:.2f} GB"


def _terabytes(bytes_num) -> str:
    tbytes = bytes_num / 10**12
    return f"{tbytes:.2f} TB"


def _dataset_raw_files(project, dataset) -> Iterable[Path]:
    master = project.get_dataset_master_image(dataset)
    prefix = master.name[: -len("master.h5")]
    return master.parent.glob(f"{prefix}*.h5")


def _dataset_raw_files_size(project, dataset):
    raw_files = _dataset_raw_files(project, dataset)
    return reduce(lambda l, r: l + r, [f.stat().st_size for f in raw_files])


def _project_raw_files_size(project):
    total = 0

    for dset in project.get_datasets():
        raw_size = _dataset_raw_files_size(project, dset)
        print(f"{dset.name} {_gigabytes(raw_size):>9}")
        total += raw_size

    print(f"total {_terabytes(total)}")


def _check_maxiv_size():
    import local_site

    if local_site.SITE.lower() != "maxiv":
        raise CommandError(f"this command is only supported at MAXIV site")


class Command(BaseCommand):
    help = "show total size of project's raw files"

    def add_arguments(self, parser):
        parser.add_argument("project_id", type=int)

    @db_session
    def handle(self, *args, **options):
        _check_maxiv_size()
        _project_raw_files_size(get_project(options["project_id"]))
