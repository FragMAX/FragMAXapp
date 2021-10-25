from unittest import TestCase
from io import BytesIO
from django import test
from fragview.models import Library, Fragment
from fragview.crystals import parse_crystals_csv, InvalidCrystalsCSV

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


class TestParse(test.TestCase):
    """
    test parsing crystals CSV file
    """

    def setUp(self):
        mylib = Library(name="FragMAXlib")
        mylib.save()

        frag = Fragment(
            library=mylib, code="VT00249", smiles="O=C1N[C@@H](CO1)C1=CC=CC=C1"
        )
        frag.save()

    def test_ok(self):
        crystals = parse_crystals_csv(BytesIO(VALID_CSV))
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


class TestParseCrystalsCsvErrors(TestCase):
    """
    test cases where we get 'syntax errors' while parsing crystals CSV
    """

    def test_csv_parse_error(self):
        """
        unparsable CSV case
        """
        with self.assertRaises(InvalidCrystalsCSV):
            parse_crystals_csv(BytesIO(b'"'))

    def test_missing_required_cols(self):
        """
        required columns are missing
        """
        with self.assertRaisesRegex(InvalidCrystalsCSV, "^Missing columns:.*"):
            parse_crystals_csv(BytesIO(MISSING_REQ_COLUMS))

    def test_unexpected_column(self):
        """
        unexpected column in the CSV
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^Unexpected column: Suprise\."
        ):
            parse_crystals_csv(BytesIO(UNEXPECTED_COLUMN))

    def test_empty_sample_id(self):
        """
        one of the crystals have an empty SampleID specified
        """
        with self.assertRaisesRegex(InvalidCrystalsCSV, r"Empty SampleID specified\."):
            parse_crystals_csv(BytesIO(EMPTY_SAMPLE_ID))


class TestFragmentLibraryErrors(test.TestCase):
    """
    test cases when there is en error specifying ligand fragment
    """

    def setUp(self):
        mylib = Library(name="MyLib")
        mylib.save()

        frag = Fragment(library=mylib, code="VT000", smiles="CN1CCCC1CO")
        frag.save()

    def test_missing_frag_library(self):
        """
        case where fragment code is present, but no library is specified
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^No fragment library specified for 'Cry2' crystal."
        ):
            parse_crystals_csv(BytesIO(MISSING_FRAG_LIBRARY))

    def test_missing_frag_code(self):
        """
        case where fragment library is specified, by there is no fragment code
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^No fragment code specified for 'Cry2' crystal."
        ):
            parse_crystals_csv(BytesIO(MISSING_FRAG_CODE))

    def test_unknown_frag_library(self):
        """
        case where unknown fragment library is specified
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^Unknown fragment library 'Wat'."
        ):
            parse_crystals_csv(BytesIO(UNKNOWN_FRAG_LIBRARY))

    def test_unknown_frag_code(self):
        """
        case where unknown fragment code is specified
        """
        with self.assertRaisesRegex(
            InvalidCrystalsCSV, r"^No fragment BT01 in 'MyLib' library."
        ):
            parse_crystals_csv(BytesIO(UNKNOW_FRAG_CODE))
