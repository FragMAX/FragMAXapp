import csv
from unittest import TestCase
from fragview import fraglib


class TestParseCSV(TestCase):
    """
    test Fragment Library file parsing function fraglib._parse_csv()
    """
    def test_valid(self):
        """
        test parsing a valid fragment library CSV file
        """
        csv_reader = csv.reader(["F1,C",
                                 "F2,CN",
                                 "",  # include an empty line
                                 ])
        frags = fraglib._parse_csv(csv_reader)

        # check that we got our expected F1 and F2 fragments
        self.assertListEqual(frags,
                             [("F1", "C"), ("F2", "CN")])

    def test_to_many_columns(self):
        """
        test parsing CSV file with wrong number of columns
        """
        csv_reader = csv.reader(["A,C,Extra"])

        with self.assertRaisesRegex(fraglib.FraglibError, "^unexpected number of cells"):
            fraglib._parse_csv(csv_reader)

    def test_invalid_smiles(self):
        """
        test parsing CSV file where SMILES is not valid
        """
        csv_reader = csv.reader(["A,WHAT"])

        with self.assertRaises(fraglib.FraglibError) as ctx:
            fraglib._parse_csv(csv_reader)

        self.assertEqual(ctx.exception.error_message(), "invalid SMILES 'WHAT' for fragment 'A'")
