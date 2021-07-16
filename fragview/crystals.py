"""
crystal list CSV file parser
"""
from typing import List
from collections import namedtuple
from pandas import read_csv, DataFrame
from fragview.models import Library, Fragment

REQUIRED_COLUMNS = [
    "SampleID",
    "FragmentLibrary",
    "FragmentCode",
    "Solvent",
    "SolventConcentration",
]


Crystal = namedtuple("Crystal", REQUIRED_COLUMNS)


class Crystals:
    def __init__(self, crystals: List[Crystal]):
        self._crystals = crystals

    def as_list(self):
        return self._crystals

    def __iter__(self):
        def _iterator(lst):
            for e in lst:
                yield e

        return _iterator(self._crystals)

    @staticmethod
    def from_data_frame(crystals: DataFrame):
        def _rows_as_crystal_tuples():
            for line_num, crystal in crystals.iterrows():
                yield Crystal(
                    crystal.SampleID,
                    crystal.FragmentLibrary,
                    crystal.FragmentCode,
                    crystal.Solvent,
                    crystal.SolventConcentration,
                )

        return Crystals(list(_rows_as_crystal_tuples()))

    @staticmethod
    def from_list(crystals):
        def _as_crystal_typles():
            for crystal in crystals:
                yield Crystal(*crystal)

        return Crystals(list(_as_crystal_typles()))


class InvalidCrystalsCSV(Exception):
    pass


def _columns_err(names):
    plural = "s" if len(names) > 1 else ""
    return f"column{plural}: {', '.join(names)}."


def _check_column_names(data: DataFrame):
    """
    check that the loaded CSV have all correct column names
    """
    column_names = set(data.columns.to_list())

    required = set(REQUIRED_COLUMNS)

    missing = required - column_names
    if missing:
        err_msg = f"Missing {_columns_err(missing)}"
        raise InvalidCrystalsCSV(err_msg)

    unexpected = column_names - required
    if unexpected:
        err_msg = f"Unexpected {_columns_err(unexpected)}"
        raise InvalidCrystalsCSV(err_msg)


def _check_fragment(library_name: str, fragment_code: str):
    """
    that that we can look-up specified fragment code in the specified
    library

    raises InvalidCrystalsCSV() if library or fragment is not found
    """
    try:
        Fragment.get(library_name, fragment_code)
    except Library.DoesNotExist:
        raise InvalidCrystalsCSV(f"Unknown fragment library '{library_name}'.")
    except Fragment.DoesNotExist:
        raise InvalidCrystalsCSV(
            f"No fragment {fragment_code} in '{library_name}' library."
        )


def _check_fragments(crystals: Crystals):
    """
    check that all specified fragments have a known
    library name and fragment code
    """
    for crystal in crystals:
        _check_fragment(crystal.FragmentLibrary, crystal.FragmentCode)


def parse_crystals_csv(csv_data: bytes) -> Crystals:
    csv = read_csv(csv_data)

    _check_column_names(csv)

    crystals = Crystals.from_data_frame(csv)
    _check_fragments(crystals)

    return crystals
