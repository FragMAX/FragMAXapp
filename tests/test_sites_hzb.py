import shutil
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from fragview.sites.hzb import SitePlugin


PROTEIN = "ARwoDMSO"
LIBRARY = "F2XEntry"
PROPOSAL = "frag200003"


def _make_image_files(proposals_dir):
    """
    create directories and dummy diffraction image files
    for HZB styled project
    """

    def _make_dset_files(protein_dir, dset_name, run):
        dset_full_name = f"{PROTEIN}-{LIBRARY}-{dset_name}"
        dset_dir = Path(protein_dir, dset_full_name)
        dset_dir.mkdir(parents=True)

        for num in range(1, 11):
            Path(dset_dir, f"{dset_full_name}_{run}_{num:04}.cbf").touch()

        # one extra CBF file, that should be ignored
        Path(dset_dir, f"ref-{dset_full_name}_{run}_0001.cbf").touch()

    protein_dir = Path(proposals_dir, PROPOSAL, "raw", PROTEIN)

    _make_dset_files(protein_dir, "Apo23", 1)
    _make_dset_files(protein_dir, "Apo32", 2)
    _make_dset_files(protein_dir, "E12a", 1)
    _make_dset_files(protein_dir, "F02a", 2)
    _make_dset_files(protein_dir, "X99c", 3)


class TestGetDatasets(TestCase):
    """
    test HZB plugin's get_project_datasets() method
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        _make_image_files(self.temp_dir)

        self.proj = Mock()
        self.proj.protein = PROTEIN
        self.proj.proposal = PROPOSAL
        self.proj.shift = ""

        self.plugin = SitePlugin()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_get_sets(self):
        # get the datasets
        with patch("fragview.projects.SITE.PROPOSALS_DIR", self.temp_dir):
            dsets = set(self.plugin.get_project_datasets(self.proj))

        # check that we got expected datasets
        self.assertSetEqual(
            dsets,
            {
                "ARwoDMSO-F2XEntry-E12a_1",
                "ARwoDMSO-F2XEntry-Apo32_2",
                "ARwoDMSO-F2XEntry-X99c_3",
                "ARwoDMSO-F2XEntry-F02a_2",
                "ARwoDMSO-F2XEntry-Apo23_1",
            },
        )
