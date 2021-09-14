"""
crystals list CSV file parser
"""
from typing import List, Optional, Dict
from pandas import read_csv, DataFrame
from pandas.errors import ParserError
from fragview import models
from dataclasses import dataclass, fields


@dataclass
class Fragment:
    library: str
    code: str


@dataclass
class Crystal:
    SampleID: str
    FragmentLibrary: Optional[str]
    FragmentCode: Optional[str]
    Solvent: str
    SolventConcentration: str

    def get_fragment(self) -> Optional[Fragment]:
        """
        get crystal's fragment description,
        returns None for apo crystals
        """
        if self.FragmentLibrary is None:
            assert self.FragmentCode is None
            return None

        # asserts for mypy's sake
        assert self.FragmentLibrary is not None
        assert self.FragmentCode is not None
        return Fragment(self.FragmentLibrary, self.FragmentCode)

    @staticmethod
    def column_names():
        for field in fields(Crystal):
            yield field.name

    def as_dict(self) -> Dict:
        cols_dict = {}
        for column_name in self.column_names():
            cols_dict[column_name] = getattr(self, column_name)

        return cols_dict


class Crystals:
    def __init__(self, crystals: List[Crystal]):
        self._crystals = crystals

    def as_list(self):
        def _generate():
            for c in self._crystals:
                yield c.as_dict()

        return list(_generate())

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
                    _sanitize_str(crystal.FragmentLibrary),
                    _sanitize_str(crystal.FragmentCode),
                    crystal.Solvent,
                    crystal.SolventConcentration,
                )

        return Crystals(list(_rows_as_crystal_tuples()))

    @staticmethod
    def from_list(crystals) -> "Crystals":
        def _as_crystal_typles():
            for crystal in crystals:
                yield Crystal(**crystal)

        return Crystals(list(_as_crystal_typles()))


class InvalidCrystalsCSV(Exception):
    pass


def _sanitize_str(val: str) -> Optional[str]:
    """
    remove leading and trailing white spaces,
    convert empty strings to None
    """
    val = val.strip()
    if val == "":
        return None

    return val


def _columns_err(names):
    plural = "s" if len(names) > 1 else ""
    return f"column{plural}: {', '.join(names)}."


def _check_column_names(data: DataFrame):
    """
    check that the loaded CSV have all correct column names
    """
    column_names = set(data.columns.to_list())

    required = set(Crystal.column_names())

    missing = required - column_names
    if missing:
        err_msg = f"Missing {_columns_err(missing)}"
        raise InvalidCrystalsCSV(err_msg)

    unexpected = column_names - required
    if unexpected:
        err_msg = f"Unexpected {_columns_err(unexpected)}"
        raise InvalidCrystalsCSV(err_msg)


def _check_fragment(crystal: Crystal):
    """
    that that we can look-up specified fragment code in the specified
    library

    raises InvalidCrystalsCSV() if library or fragment is not found
    """
    library_name = crystal.FragmentLibrary
    fragment_code = crystal.FragmentCode

    if library_name is None and fragment_code is None:
        # apo crystal
        return

    if library_name is None:
        raise InvalidCrystalsCSV(
            f"No fragment library specified for '{crystal.SampleID}' crystal."
        )

    if fragment_code is None:
        raise InvalidCrystalsCSV(
            f"No fragment code specified for '{crystal.SampleID}' crystal."
        )

    try:
        models.Fragment.get(library_name, fragment_code)
    except models.Library.DoesNotExist:
        raise InvalidCrystalsCSV(f"Unknown fragment library '{library_name}'.")
    except models.Fragment.DoesNotExist:
        raise InvalidCrystalsCSV(
            f"No fragment {fragment_code} in '{library_name}' library."
        )


def _check_fragments(crystals: Crystals):
    """
    check that all specified fragments have a known
    library name and fragment code
    """
    for crystal in crystals:
        _check_fragment(crystal)


def parse_crystals_csv(csv_data: bytes) -> Crystals:
    """
    Parse specified data as 'Crystals CSV' file.

    Perform some semantic checks on specified crystals, for example
    check if specified fragment's library and code are known by the app.

    raises InvalidCrystalsCSV exception if invalid data is detected
    """
    try:
        csv = read_csv(
            csv_data,
            # don't convert empty strings to float NaN values
            na_filter=False,
        )
    except ParserError as e:
        raise InvalidCrystalsCSV(f"{e}")

    _check_column_names(csv)

    crystals = Crystals.from_data_frame(csv)
    _check_fragments(crystals)

    return crystals
