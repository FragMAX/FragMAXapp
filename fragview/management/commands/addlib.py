from typing import Dict
import yaml
from pathlib import Path
from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from fragview.models import Library, Fragment


def _load_yml(yml_file: Path):
    with yml_file.open() as f:
        return yaml.safe_load(f)


@transaction.atomic
def _create_library(lib_desc: Dict):
    lib_name = lib_desc["name"]

    # check if this library already exist
    if Library.objects.filter(name=lib_name).exists():
        raise CommandError(
            f"Fragments library '{lib_name}' already exists, refusing to overwrite."
        )

    lib = Library(name=lib_name)
    lib.save()

    for code, smiles in lib_desc["fragments"].items():
        frag = Fragment(library=lib, code=code, smiles=smiles)
        frag.save()

    num_frags = len(lib_desc["fragments"].keys())
    print(f"added library '{lib_name}' with {num_frags} fragments")


class Command(BaseCommand):
    help = "add fragments library"

    def add_arguments(self, parser):
        # TODO: document fragments library definition file format
        # TODO: add support to override existing library
        parser.add_argument(
            "library_file",
            type=str,
            help="Library definition file.\nSee FragMAX documentation for file format.",
        )

    def handle(self, *args, **options):
        yml_file = Path(options["library_file"])

        if not yml_file.is_file():
            raise CommandError(f"can't read file: {yml_file}")

        lib = _load_yml(yml_file)
        _create_library(lib)
