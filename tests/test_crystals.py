from unittest import TestCase
from io import BytesIO
from fragview import crystals
from fragview.crystals import parse_crystals_csv, InvalidCrystalsCSV, Crystals, Crystal
from tests.utils import ProjectTestCase

VALID_CSV = b"""SampleID,FragmentLibrary,FragmentCode
MID2-x0017,FragMAXlib,VT00249
MID2-x0018,FragMAXlib,VT00249
MID2-x0019,,
"""

MISSING_REQ_COLUMS = b"""Col1,Col2
v1,v2"""

UNEXPECTED_COLUMN = b"""SampleID,FragmentCode,FragmentLibrary,Suprise
val1,val2,val3,val4
"""

EMPTY_SAMPLE_ID = b"""SampleID,FragmentLibrary,FragmentCode
,,
"""

MISSING_FRAG_LIBRARY = b"""SampleID,FragmentLibrary,FragmentCode
Cry1,MyLib,VT000
Cry2,,VT000
"""

MISSING_FRAG_CODE = b"""SampleID,FragmentLibrary,FragmentCode
Cry1,MyLib,VT000
Cry2,MyLib,
"""

UNKNOWN_FRAG_LIBRARY = b"""SampleID,FragmentLibrary,FragmentCode
Cry1,Wat,VT000
"""

UNKNOW_FRAG_CODE = b"""SampleID,FragmentLibrary,FragmentCode
Cry1,MyLib,BT01
"""


class TestParse(TestCase):
    """
    test parsing crystals CSV file
    """

    LIBRARIES = {"FragMAXlib": {"VT00249": "O=C1N[C@@H](CO1)C1=CC=CC=C1"}}

    def test_ok(self):
        crystals = parse_crystals_csv(self.LIBRARIES, BytesIO(VALID_CSV))
        self.assertListEqual(
            crystals.as_list(),
            [
                {
                    "SampleID": "MID2-x0017",
                    "FragmentLibrary": "FragMAXlib",
                    "FragmentCode": "VT00249",
                },
                {
                    "SampleID": "MID2-x0018",
                    "FragmentLibrary": "FragMAXlib",
                    "FragmentCode": "VT00249",
                },
                {
                    "SampleID": "MID2-x0019",
                    "FragmentLibrary": None,
                    "FragmentCode": None,
                },
            ],
        )


class TestCrystal(TestCase):
    def test_get_fragment(self):
        """
        test Crystal.get_fragment() method
        """
        crystal = Crystal("FOO-x01", "Lib", "E23")
        fragment = crystal.get_fragment()

        self.assertEqual(fragment, crystals.Fragment("Lib", "E23"))

    def test_get_fragment_apo(self):
        """
        test Crystal.get_fragment() method on an Apo crystal
        """
        crystal = Crystal("FOO-x01", None, None)
        fragment = crystal.get_fragment()

        self.assertIsNone(fragment)


class TestFromList(TestCase):
    """
    test Crystals.from_list()
    """

    EXPECTED_CRYSTALS = {
        "MID2-x0017": Crystal("MID2-x0017", "FragMAXlib", "VT00249"),
        "MID2-x0019": Crystal("MID2-x0019", None, None),
    }

    def test_from_list(self):
        #
        # 'deserialize' Crystals from a list of dicts
        #
        crystals = Crystals.from_list(
            [
                {
                    "SampleID": "MID2-x0017",
                    "FragmentLibrary": "FragMAXlib",
                    "FragmentCode": "VT00249",
                },
                {
                    "SampleID": "MID2-x0019",
                    "FragmentLibrary": None,
                    "FragmentCode": None,
                },
            ]
        )

        #
        # check that we got the expected set if Crystal objects
        #
        num_crystals = 0
        for crystal in crystals:
            expected_crystal = self.EXPECTED_CRYSTALS[crystal.SampleID]
            self.assertEqual(crystal, expected_crystal)
            num_crystals += 1

        self.assertEqual(num_crystals, len(self.EXPECTED_CRYSTALS))


class TestParseCrystalsCsvErrors(ProjectTestCase):
    """
    test cases where we get 'syntax errors' while parsing crystals CSV
    """

    def test_csv_parse_error(self):
        """
        unparsable CSV case
        """
        with self.assertRaises(InvalidCrystalsCSV):
            parse_crystals_csv(self.project, BytesIO(b'"'))

    def test_missing_required_cols(self):
        """
        required columns are missing
        """
        with self.assertRaisesRegex(InvalidCrystalsCSV, "^Missing columns:.*"):
            parse_crystals_csv(self.project, BytesIO(MISSING_REQ_COLUMS))

    def test_unexpected_column(self):
        """
        unexpected column in the CSV
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^Unexpected column: Suprise\."
        ):
            parse_crystals_csv(self.project, BytesIO(UNEXPECTED_COLUMN))

    def test_empty_sample_id(self):
        """
        one of the crystals have an empty SampleID specified
        """
        with self.assertRaisesRegex(InvalidCrystalsCSV, r"Empty SampleID specified\."):
            parse_crystals_csv(self.project, BytesIO(EMPTY_SAMPLE_ID))


class TestFragmentLibraryErrors(TestCase):
    """
    test cases when there is en error specifying ligand fragment
    """

    LIBRARIES = {"MyLib": {"VT000": "CN1CCCC1CO"}}

    def test_missing_frag_library(self):
        """
        case where fragment code is present, but no library is specified
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^No fragment library specified for 'Cry2' crystal."
        ):
            parse_crystals_csv(self.LIBRARIES, BytesIO(MISSING_FRAG_LIBRARY))

    def test_missing_frag_code(self):
        """
        case where fragment library is specified, by there is no fragment code
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^No fragment code specified for 'Cry2' crystal."
        ):
            parse_crystals_csv(self.LIBRARIES, BytesIO(MISSING_FRAG_CODE))

    def test_unknown_frag_library(self):
        """
        case where unknown fragment library is specified
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^Unknown fragment library 'Wat'."
        ):
            parse_crystals_csv(self.LIBRARIES, BytesIO(UNKNOWN_FRAG_LIBRARY))

    def test_unknown_frag_code(self):
        """
        case where unknown fragment code is specified
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^No fragment BT01 in 'MyLib' library."
        ):
            parse_crystals_csv(self.LIBRARIES, BytesIO(UNKNOW_FRAG_CODE))
