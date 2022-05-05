"""
parsing and validation of Fragment Library CSV and YML files
"""
from typing import Dict, Tuple, Optional
import yaml
from pathlib import Path
from pandas import read_csv, DataFrame
from pandas.errors import ParserError
from django.db import transaction
from fragview import models
from fragview.projects import Project

CSV_COLUMN_NAMES = {"fragmentCode", "SMILES"}

LibraryType = Dict[str, str]


class InvalidLibraryCSV(Exception):
    pass


class LibraryAlreadyExist(Exception):
    pass


@transaction.atomic
def create_db_library(project: Optional[Project], name: str, fragments: Dict[str, str]):
    # check if this library already exist
    if models.Library.get_all(project).filter(name=name).exists():
        raise LibraryAlreadyExist(
            f"Fragments library '{name}' already exists, refusing to overwrite."
        )

    lib = models.Library(name=name)
    if project is not None:
        # mark as project private library
        lib.project_id = project.id
    lib.save()

    for code, smiles in fragments.items():
        models.Fragment(library=lib, code=code, smiles=smiles).save()


def parse_fraglib_yml(yml_file: Path) -> Tuple[str, Dict[str, str]]:
    def _load_yml():
        with yml_file.open() as f:
            return yaml.safe_load(f)

    yml = _load_yml()

    # TODO: validate smiles
    return yml["name"], yml["fragments"]


def _check_csv_column_names(data: DataFrame):
    """
    check that the loaded CSV have all correct column names
    """

    missing = set()

    column_names = {name for name in data.columns}
    for req in CSV_COLUMN_NAMES:
        if req not in column_names:
            missing.add(req)

    if missing:
        missing_names = "', '".join(missing)
        plural = "s" if len(missing) > 1 else ""
        raise InvalidLibraryCSV(f"CSV is missing '{missing_names}' column{plural}.")


def parse_fraglib_csv(csv_data) -> LibraryType:
    try:
        csv = read_csv(
            csv_data,
            # don't convert empty strings to float NaN values
            na_filter=False,
        )
    except ParserError as e:
        raise InvalidLibraryCSV(f"{e}")

    _check_csv_column_names(csv)

    frags = {}

    for line_num, entry in csv.iterrows():
        frags[entry.fragmentCode] = entry.SMILES

    return frags
