from unittest import TestCase
from io import BytesIO
from fragview.crystals import parse_crystals_csv, InvalidCrystalsCSV

EMPTY_SAMPLE_ID = BytesIO(
    b"""
SampleID,FragmentLibrary,FragmentCode
,,
"""
)


class TestParseCrystalsCsv(TestCase):
    """
    test parsing crystals CSV
    """

    def test_empty_sample_id(self):
        with self.assertRaisesRegex(InvalidCrystalsCSV, r"Empty SampleID specified\."):
            parse_crystals_csv(EMPTY_SAMPLE_ID)
