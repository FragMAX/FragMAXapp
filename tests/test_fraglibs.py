from io import BytesIO
from unittest import TestCase
from fragview.models import Library
from fragview.fraglibs import (
    parse_fraglib_yml,
    parse_fraglib_csv,
    create_db_library,
    InvalidLibraryCSV,
    LibraryAlreadyExist,
)
from tests.utils import data_file_path, ProjectTestCase

FRAGMENTS = {
    "F00": "C1CCO[C@H](C1)C[NH3+]",
    "F01": "c1c(ncs1)C2CC2",
    "F02": "c1cc(cc(c1)Cl)CO",
    "F03": "c1cc(nc(c1)N)C(F)(F)F",
    "F04": "OC1CCCC2CCCC12",
}

FRAGMENTS_CSV = b"""fragmentCode,SMILES
F00,C1CCO[C@H](C1)C[NH3+]
F01,c1c(ncs1)C2CC2
F02,c1cc(cc(c1)Cl)CO
F03,c1cc(nc(c1)N)C(F)(F)F
F04,OC1CCCC2CCCC12
"""


class TestCreateDBLibrary(ProjectTestCase):
    def _assert_library(self, project, name, fragments):
        lib = Library.get_by_name(project, name)
        self.assertDictEqual(lib.as_dict(), fragments)

        expected_id = None if project is None else str(project.id)
        self.assertEqual(expected_id, lib.project_id)

    def test_ok(self):
        # new public library
        create_db_library(None, "Public", FRAGMENTS)
        self._assert_library(None, "Public", FRAGMENTS)

        # new private library
        create_db_library(self.project, "Private", FRAGMENTS)
        self._assert_library(self.project, "Private", FRAGMENTS)

    def test_already_exist(self):
        # already existing public library
        Library(name="MyLib").save()
        with self.assertRaises(LibraryAlreadyExist):
            create_db_library(None, "MyLib", FRAGMENTS)

        # already existing private library
        Library(name="MyPrivLib", project_id=self.project.id).save()
        with self.assertRaises(LibraryAlreadyExist):
            create_db_library(self.project, "MyPrivLib", FRAGMENTS)


class TestParseFraglibYML(TestCase):
    def test_ok(self):
        name, frags = parse_fraglib_yml(data_file_path("fraglib.yml"))

        self.assertEqual(name, "TestLib")
        self.assertDictEqual(frags, FRAGMENTS)


class TestParseFraglibCSV(TestCase):
    def test_ok(self):
        frags = parse_fraglib_csv(BytesIO(FRAGMENTS_CSV))

        self.assertDictEqual(frags, FRAGMENTS)

    def test_missing_cols(self):
        csv = BytesIO(b"fragmentCode,Cols\nhere,hepp")

        with self.assertRaises(InvalidLibraryCSV) as ctx:
            parse_fraglib_csv(csv)

        # check that we got expected error message
        self.assertEqual(str(ctx.exception), "CSV is missing 'SMILES' column.")

    def test_invalid_csv(self):
        csv = BytesIO(b'"')

        with self.assertRaisesRegexp(InvalidLibraryCSV, "Error token"):
            parse_fraglib_csv(csv)
