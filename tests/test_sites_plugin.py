from unittest import TestCase
from fragview.sites.plugin import DataSize


class TestDataSize(TestCase):
    """
    test DataSize class
    """

    def test_no_value(self):
        """
        it should not be possible to create DataSize without any arguments
        """
        with self.assertRaisesRegex(ValueError, "no size value specified"):
            DataSize()

    def test_multiple_values(self):
        """
        only one size unit can be used at the time
        """
        with self.assertRaisesRegex(ValueError, "multiple size units not supported"):
            DataSize(kilobyte=1, megabyte=3)

    def _assert_value_unit(self, data_size, expected_value, expected_unit):
        self.assertEqual(data_size.value, expected_value)
        self.assertEqual(data_size.unit, expected_unit)

    def test_ok(self):
        """
        check that all supported size units work
        """
        self._assert_value_unit(DataSize(gigabyte=2), 2, "G")
        self._assert_value_unit(DataSize(megabyte=14), 14, "M")
        self._assert_value_unit(DataSize(kilobyte=47), 47, "K")
