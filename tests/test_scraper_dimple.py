from pathlib import Path
from shutil import copyfile
from unittest import TestCase
from unittest.mock import Mock
from tests.utils import TempDirMixin, data_file_path
from fragview.scraper.dimple import _scrape_blobs


class TestScrapeBlobs(TestCase, TempDirMixin):
    """
    test _scrape_blobs() function
    """

    def setUp(self):
        self.project = Mock()
        self.setup_temp_dir()

    def tearDown(self):
        self.tear_down_temp_dir()

    def setup_dimple_log(self, test_log):
        src = data_file_path(test_log)
        dest = Path(self.temp_dir, "dimple.log")
        copyfile(src, dest)

    def test_ok(self):
        self.setup_dimple_log("dimple_blobs.log")

        blobs = _scrape_blobs(self.project, self.temp_dir)
        self.assertEquals(
            blobs,
            "[[9.5, 2.21, 18.98], [15.74, -16.55, 33.79], [18.88, 5.64, 3.49], "
            "[11.19, 9.51, 1.17], [31.63, 4.21, 20.67], [29.7, -9.9, 9.92], "
            "[19.59, 3.02, 27.47], [23.53, -3.2, 17.05]]",
        )

    def test_no_blobs(self):
        """
        test parsing log for a run where dimple did not find any blobs
        """
        self.setup_dimple_log("dimple_no_blobs.log")

        blobs = _scrape_blobs(self.project, self.temp_dir)
        self.assertEquals(
            blobs,
            "[]",
        )
