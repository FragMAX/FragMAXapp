import shutil
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from fragview.projects import project_all_status_file, project_data_collections_file
from fragview.filters import get_proc_datasets, get_refine_datasets, get_ligfit_datasets
from tests.utils import data_file_path


PROTEIN = "PrtK"
PROPOSAL = "20180479"
SHIFTS = ["20191022", "20191023"]
DATASETS = [
    "PrtK-Apo14_1",
    "PrtK-Apo9_1",
    "PrtK-JBS-G8a_1",
    "PrtK-JBS-F3a_1",
    "PrtK-JBS-D10a_1",
    "PrtK-JBS-D12a_1",
]

DATACOLLECTION_CSV = """imagePrefix,SampleName,dataCollectionPath,Acronym,dataCollectionNumber,numberOfImages,resolution,snapshot
PrtK-Apo14,Apo14,/data/visitors/biomax/20180479/20191022/raw/PrtK/PrtK-Apo14,PrtK,1,3600,1.24,"/mxn/groups/ispybstorage/pyarch/visitors/20180479/20191022/raw/PrtK/PrtK-Apo14/PrtK-Apo14_1_1.snapshot.jpeg,/mxn/groups/ispybstorage/pyarch/visitors/20180479/20191022/raw/PrtK/PrtK-Apo14/PrtK-Apo14_1_2.snapshot.jpeg"
"""

Site = Mock()
Site.get_project_datasets.return_value = DATASETS


def _copy_csv_files(proj):
    all_stat = Path(project_all_status_file(proj))
    all_stat.parent.mkdir(parents=True)

    shutil.copy(data_file_path("allstatus.csv"), all_stat)
    shutil.copy(
        data_file_path("datacollections.csv"), project_data_collections_file(proj)
    )


def _create_dirs(root):
    #
    # create results dirs for some datasets
    #
    res_dir = Path(root, "fragmax", "results")

    # dataset #0 (PrtK-Apo14_1)
    apo14_res_dir = Path(res_dir, DATASETS[0])
    apo14_res_dir.mkdir(parents=True)

    # dataset #2 (PrtK-JBS-G8a_1)
    g8a_res_dir = Path(res_dir, DATASETS[2])
    g8a_res_dir.mkdir(parents=True)

    # dataset #3 (PrtK-JBS-F3a_1)
    f3a_res_dir = Path(res_dir, DATASETS[3])
    f3a_res_dir.mkdir(parents=True)

    # dataset #5 (PrtK-JBS-F3a_1)
    d12a_res_dir = Path(res_dir, DATASETS[5])
    d12a_res_dir.mkdir(parents=True)


class _FiltersTester(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        self.proj = Mock()
        self.proj.protein = PROTEIN
        self.proj.data_path.return_value = self.temp_dir

        _create_dirs(self.temp_dir)
        _copy_csv_files(self.proj)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)


@patch("fragview.projects.SITE", Site)
class TestGetProcDatasets(_FiltersTester):
    """
    test get_proc_datasets(), the dataset filtering for 'data processing' jobs
    """

    def test_all(self):
        """
        test the 'ALL' filter
        """
        dsets = get_proc_datasets(self.proj, "ALL")

        self.assertListEqual(DATASETS, dsets)

    def test_new(self):
        """
        test 'NEW' filter
        """
        dsets = get_proc_datasets(self.proj, "NEW")

        self.assertListEqual(["PrtK-Apo9_1", "PrtK-JBS-D10a_1"], list(dsets))

    def test_selected(self):
        """
        test the filter where datasets are explicitly specified
        """
        dsets = get_proc_datasets(self.proj, "PrtK-Apo9_1,PrtK-JBS-G8a_1")

        self.assertListEqual(["PrtK-Apo9_1", "PrtK-JBS-G8a_1"], list(dsets))


@patch("fragview.projects.SITE", Site)
class TestGetRefineDatasets(_FiltersTester):
    """
    test get_refine_datasets()
    """

    def test_all(self):
        """
        test the 'ALL' filter
        """
        dsets = get_refine_datasets(self.proj, "ALL", True, True, True)

        self.assertListEqual(DATASETS, dsets)

    def test_new_all_tools(self):
        """
        test 'NEW' filter, with all refine tools selected
        """
        dsets = get_refine_datasets(self.proj, "NEW", True, True, True)

        self.assertListEqual(
            [
                "PrtK-Apo55_1",
                "PrtK-Apo2_1",
                "PrtK-Apo5_1",
                "PrtK-JBS-G8a_1",
                "PrtK-JBS-C1a_1",
                "PrtK-JBS-H8a_1",
                "PrtK-JBS-B7a_1",
                "PrtK-JBS-H4a_2",
                "PrtK-JBS-B8a_1",
            ],
            list(dsets),
        )

    def test_new_fspipeline(self):
        """
        test 'NEW' filter, with fspipeline selected
        """
        dsets = get_refine_datasets(self.proj, "NEW", True, False, False)

        self.assertListEqual(["PrtK-JBS-H8a_1", "PrtK-JBS-B7a_1"], list(dsets))

    def test_new_dimple(self):
        """
        test 'NEW' filter, with dimple selected
        """
        dsets = get_refine_datasets(self.proj, "NEW", False, True, False)

        self.assertListEqual(["PrtK-JBS-G8a_1", "PrtK-JBS-B8a_1"], list(dsets))

    def test_new_buster(self):
        """
        test 'NEW' filter, with buster selected
        """
        dsets = get_refine_datasets(self.proj, "NEW", False, False, True)

        # from pprint import pprint
        # pprint(list(dsets))

        self.assertListEqual(
            [
                "PrtK-Apo55_1",
                "PrtK-Apo2_1",
                "PrtK-Apo5_1",
                "PrtK-JBS-G8a_1",
                "PrtK-JBS-C1a_1",
                "PrtK-JBS-H4a_2",
            ],
            list(dsets),
        )

    def test_selected(self):
        """
        test the filter where datasets are explicitly specified
        """
        dsets = get_refine_datasets(
            self.proj, "PrtK-Apo9_1,PrtK-JBS-G8a_1", True, True, True
        )

        self.assertListEqual(["PrtK-Apo9_1", "PrtK-JBS-G8a_1"], list(dsets))


@patch("fragview.projects.SITE", Site)
class TestGetLigfitDatasets(_FiltersTester):
    """
    test get_ligfit_datasets()
    """

    def test_all(self):
        """
        test the 'ALL' filter
        """
        dsets = get_ligfit_datasets(self.proj, "ALL", True, True)

        self.assertListEqual(
            ["PrtK-JBS-G8a_1", "PrtK-JBS-F3a_1", "PrtK-JBS-D10a_1", "PrtK-JBS-D12a_1"],
            list(dsets),
        )

    def test_new_all_tools(self):
        """
        test 'NEW' filter with both rhfit and ligandfit tools selected
        """
        dsets = get_ligfit_datasets(self.proj, "NEW", True, True)

        self.assertListEqual(
            ["PrtK-JBS-A12a_1", "PrtK-JBS-H2a_2", "PrtK-JBS-H11a_1"], list(dsets)
        )

    def test_new_ligand_fit(self):
        """
        test 'NEW' filter with ligandfit selected
        """
        dsets = get_ligfit_datasets(self.proj, "NEW", True, False)

        self.assertListEqual(["PrtK-JBS-A12a_1", "PrtK-JBS-H2a_2"], list(dsets))

    def test_new_rho_fit(self):
        """
        test 'NEW' filter with rho_fit selected
        """
        dsets = get_ligfit_datasets(self.proj, "NEW", False, True)

        self.assertListEqual(["PrtK-JBS-H11a_1"], list(dsets))

    def test_selected(self):
        """
        test the filter where datasets are explicitly specified
        """
        dsets = get_ligfit_datasets(
            self.proj, "PrtK-JBS-F3a_1,PrtK-JBS-D10a_1", True, True
        )

        self.assertListEqual(["PrtK-JBS-F3a_1", "PrtK-JBS-D10a_1"], list(dsets))