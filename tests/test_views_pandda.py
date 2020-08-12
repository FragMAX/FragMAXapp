from unittest import TestCase
from unittest.mock import Mock
from fragview.views.pandda import _get_pdb_data
from tests.utils import data_file_path


class TestGetPdbData(TestCase):
    """
    test pandda._get_pdb_data() function
    """
    def setUp(self):
        self.proj = Mock()
        self.proj.encrypted = False

    def _assert_pdb(
        self, pdb_path, expected_r_work, expected_r_free, expected_resolution
    ):
        r_work, r_free, resolution = _get_pdb_data(self.proj, pdb_path)

        self.assertEqual(r_work, expected_r_work)
        self.assertEqual(r_free, expected_r_free)
        self.assertEqual(resolution, expected_resolution)

    def test_func(self):
        self._assert_pdb(data_file_path("final0.pdb"), "0.15379", "0.16958", "1.08")
        self._assert_pdb(data_file_path("final1.pdb"), "0.17733", "0.20282", "1.06")
        self._assert_pdb(data_file_path("refine0.pdb"), "0.2882", "0.3279", "1.116")
        self._assert_pdb(data_file_path("refine1.pdb"), "", "", "")
