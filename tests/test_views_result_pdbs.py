import os
import tempfile
from os import path
from unittest.mock import patch
from django import test
from tests.utils import ViewTesterMixin


class TestFinalView(test.TestCase, ViewTesterMixin):
    DATASET = "DS"
    PROCESS = "proc"
    REFINE = "ref"
    PDB_CONTENT = b"DUMMY_PDB_DATA"
    URL = f"/pdbs/final/{DATASET}/{PROCESS}/{REFINE}"

    def setUp(self):
        self.setup_client()
        self.setup_project()

    def _create_pdb(self, root_dir):
        pdb_dir = path.join(root_dir, self.DATASET, self.PROCESS, self.REFINE)
        os.makedirs(pdb_dir)

        with open(path.join(pdb_dir, "final.pdb"), "wb") as f:
            f.write(self.PDB_CONTENT)

    @patch("fragview.views.result_pdbs.project_results_dir")
    def test_plain(self, res_dir_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            res_dir_mock.return_value = temp_dir
            self._create_pdb(temp_dir)

            # request the contents of the final.pdb
            resp = self.client.get(self.URL)

            # check that we successfully got PDBs content
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content, self.PDB_CONTENT)
