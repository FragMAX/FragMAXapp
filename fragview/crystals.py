"""
crystals list CSV file parser
"""
from typing import List, Optional, Dict, Iterable
from pandas import read_csv, DataFrame
from pandas.errors import ParserError
from fragview.fraglibs import LibraryType
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
    def column_names() -> Iterable[str]:
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


def _check_fragment(frag_libs: Dict[str, LibraryType], crystal: Crystal):
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

    lib = frag_libs.get(library_name)
    if lib is None:
        raise InvalidCrystalsCSV(f"Unknown fragment library '{library_name}'.")

    if fragment_code not in lib:
        raise InvalidCrystalsCSV(
            f"No fragment {fragment_code} in '{library_name}' library."
        )


def _check_fragments(frag_libs: Dict[str, LibraryType], crystals: Crystals):
    """
    check that all specified fragments have a known
    library name and fragment code
    """
    for crystal in crystals:
        _check_fragment(frag_libs, crystal)


def _data_frame_to_crystals(
    sample_id_idx: int, fraglib_idx: int, frag_code_idx: int, crystals: DataFrame
) -> Crystals:
    def _rows_as_crystal_tuples():
        for line_num, crystal in crystals.iterrows():
            sample_id = _sanitize_str(crystal[sample_id_idx])
            # make sure SampleID is specified
            if sample_id is None:
                raise InvalidCrystalsCSV("Empty SampleID specified.")

            yield Crystal(
                sample_id,
                _sanitize_str(crystal[fraglib_idx]),
                _sanitize_str(crystal[frag_code_idx]),
            )

    return Crystals(list(_rows_as_crystal_tuples()))


def _get_column_indices(csv: DataFrame):
    """
    looks up indices for each column name in a case-insensitive way

    will raise InvalidCrystalsCSV exception
    on unexpected or missing columns
    """
    indices: Dict[str, Optional[int]] = {
        name.lower(): None for name in Crystal.column_names()
    }

    unexpected = []
    for idx, col_name in enumerate(csv.columns):
        name = col_name.lower()

        if name not in indices:
            unexpected.append(col_name)
            continue

        indices[name] = idx

    if unexpected:
        err_msg = f"Unexpected {_columns_err(unexpected)}"
        raise InvalidCrystalsCSV(err_msg)

    #
    # check if any columns are missing
    #
    missing = []
    for name in Crystal.column_names():
        if indices[name.lower()] is None:
            missing.append(name)
    if missing:
        err_msg = f"Missing {_columns_err(missing)}"
        raise InvalidCrystalsCSV(err_msg)

    return indices["sampleid"], indices["fragmentlibrary"], indices["fragmentcode"]


def parse_crystals_csv(frag_libs: Dict[str, LibraryType], csv_data) -> Crystals:
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

    sample_id_idx, fraglib_idx, frag_code_idx = _get_column_indices(csv)
    crystals = _data_frame_to_crystals(sample_id_idx, fraglib_idx, frag_code_idx, csv)
    _check_fragments(frag_libs, crystals)

    return crystals
