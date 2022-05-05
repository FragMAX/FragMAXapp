from typing import Dict
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from fragview.fraglibs import parse_fraglib_yml, create_db_library, LibraryAlreadyExist


def _create_library(name: str, fragments: Dict[str, str]):
    try:
        create_db_library(None, name, fragments)
    except LibraryAlreadyExist as e:
        raise CommandError(f"{e}")

    num_frags = len(fragments.items())
    print(f"added library '{name}' with {num_frags} fragments")


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

        name, fragmens = parse_fraglib_yml(yml_file)
        _create_library(name, fragmens)
