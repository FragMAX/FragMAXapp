import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
from django import test
from fragview import encryption
from fragview.models import EncryptionKey
from fragview.views.pandda import _get_pdb_data
from fragview.fileio import open_proj_file
from fragview.projects import project_pandda_results_dir
from tests.utils import data_file_path, ViewTesterMixin


class TestGetPdbData(unittest.TestCase):
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


@patch("fragview.models.Project.data_path")
class TestClusterImage(test.TestCase, ViewTesterMixin):
    """
    test cluster_image() view function,

    the view that serves PanDDa cluster images
    """

    METHOD = "test_meth"
    CLUSTER = "test_clu"
    DUMMY_PNG_DATA = b"faux_png"
    PNG_MIME = "image/png"

    def setUp(self):
        self.setup_client()

        self.temp_dir = tempfile.mkdtemp()
        self.mock_data_path = Mock(return_value=self.temp_dir)

    def _get_url(self):
        return f"/pandda/cluster/{self.METHOD}/{self.CLUSTER}/image"

    def _get_png_path(self):
        return Path(
            project_pandda_results_dir(self.proj),
            self.METHOD,
            "clustered-datasets",
            "dendrograms",
            f"{self.CLUSTER}.png",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_png_not_found(self, mock_data_path):
        """
        test the case where specified cluster is not found
        """
        mock_data_path.return_value = self.temp_dir
        self.setup_project()

        resp = self.client.get(self._get_url())

        self.assert_not_found_response(resp, "^no dendrogram image for")

    def test_png_plain_text(self, mock_data_path):
        """
        test fetching cluster PNG image for plain text project
        """
        mock_data_path.return_value = self.temp_dir
        self.setup_project()

        png_path = self._get_png_path()
        png_path.parent.mkdir(parents=True)
        png_path.write_bytes(self.DUMMY_PNG_DATA)

        resp = self.client.get(self._get_url())
        self.assert_response_equals(resp, 200, self.DUMMY_PNG_DATA, self.PNG_MIME)

    def test_png_encrypted(self, mock_data_path):
        """
        test fetching cluster PNG image for encrypted project
        """

        mock_data_path.return_value = self.temp_dir

        #
        # set-up encrypted project, with uploaded encryption key
        #
        self.setup_project(encrypted=True)
        key = EncryptionKey(key=encryption.generate_key(), project=self.proj)
        key.save()

        #
        # store the PNG encrypted in the correct sub-folder
        #
        png_path = self._get_png_path()
        png_path.parent.mkdir(parents=True)

        with open_proj_file(self.proj, str(png_path)) as f:
            f.write(self.DUMMY_PNG_DATA)

        # check that we got correctly decrypted PNG response
        resp = self.client.get(self._get_url())
        self.assert_response_equals(resp, 200, self.DUMMY_PNG_DATA, self.PNG_MIME)
