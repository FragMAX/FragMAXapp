import shutil
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from fragview.projects import (
    project_results_dir,
    project_all_status_file,
    project_data_collections_file,
    shift_dir,
)
from fragview.filters import (
    get_proc_datasets,
    get_refine_datasets,
    get_ligfit_datasets,
    get_ligfit_pdbs,
)
from tests.utils import data_file_path, TempDirMixin


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

Site = Mock()
Site.get_project_datasets.return_value = DATASETS


def _copy_csv_files(proj):
    all_stat = Path(project_all_status_file(proj))
    all_stat.parent.mkdir(parents=True)

    shutil.copy(data_file_path("allstatus.csv"), all_stat)
    shutil.copy(
        data_file_path("datacollections.csv"), project_data_collections_file(proj)
    )


def _create_result_dirs(proj):
    #
    # create results dirs for some datasets
    #
    res_dir = project_results_dir(proj)

    # dataset #0 (PrtK-Apo14_1)
    apo14_res_dir = Path(res_dir, DATASETS[0])
    apo14_res_dir.mkdir(parents=True)

    # dataset #2 (PrtK-JBS-G8a_1)
    g8a_res_dir = Path(res_dir, DATASETS[2])
    g8a_res_dir.mkdir(parents=True)

    # dataset #3 (PrtK-JBS-F3a_1)
    f3a_res_dir = Path(res_dir, DATASETS[3])
    f3a_res_dir.mkdir(parents=True)

    # dataset #5 (PrtK-JBS-D12a_1)
    d12a_res_dir = Path(res_dir, DATASETS[5])
    d12a_res_dir.mkdir(parents=True)


def _create_pdbs(proj):
    #
    # create some (dummy) final.pdb files inside result dirs
    # for a couple of datasets
    #

    def _touch(file_path):
        file_path.parent.mkdir(parents=True)
        file_path.touch()

    res_dir = project_results_dir(proj)

    # dataset #0 (PrtK-Apo14_1)
    apo14_res_dir = Path(res_dir, DATASETS[0])
    _touch(Path(apo14_res_dir, "dials", "fspipeline", "final.pdb"))
    _touch(Path(apo14_res_dir, "dials", "dimple", "final.pdb"))
    _touch(Path(apo14_res_dir, "xdsapp", "dimple", "final.pdb"))

    # dataset #3 (PrtK-JBS-F3a_1)
    f3a_res_dir = Path(res_dir, DATASETS[3])
    _touch(Path(f3a_res_dir, "autoproc", "dimple", "final.pdb"))
    _touch(Path(f3a_res_dir, "dials", "dimple", "final.pdb"))

    # create one folder named 'final.pdb', to check that we only find
    # PDB _files_ when listing final PDBs for ligfit tools
    d12a_res_dir = Path(res_dir, DATASETS[5])
    Path(d12a_res_dir, "dials", "dimple", "final.pdb").mkdir(parents=True)


class _FiltersTester(TestCase, TempDirMixin):
    def setUp(self):
        self.setup_temp_dir()
        Site.PROPOSALS_DIR = self.temp_dir

        with patch("fragview.projects.SITE", Site):
            self.proj = Mock()
            self.proj.protein = PROTEIN
            self.proj.proposal = PROPOSAL
            self.proj.shifts.return_value = SHIFTS
            self.proj.data_path.return_value = shift_dir(PROPOSAL, SHIFTS[0])

            _create_result_dirs(self.proj)

        _copy_csv_files(self.proj)
        _create_pdbs(self.proj)

    def tearDown(self):
        self.tear_down_temp_dir()


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
        dsets = get_refine_datasets(self.proj, "ALL", None)

        self.assertListEqual(DATASETS, dsets)

    def test_new_fspipeline(self):
        """
        test 'NEW' filter, with fspipeline selected
        """
        dsets = get_refine_datasets(self.proj, "NEW", "fspipeline")

        self.assertListEqual(["PrtK-JBS-H8a_1", "PrtK-JBS-B7a_1"], list(dsets))

    def test_new_dimple(self):
        """
        test 'NEW' filter, with dimple selected
        """
        dsets = get_refine_datasets(self.proj, "NEW", "dimple")

        self.assertListEqual(["PrtK-JBS-G8a_1", "PrtK-JBS-B8a_1"], list(dsets))

    def test_selected(self):
        """
        test the filter where datasets are explicitly specified
        """
        dsets = get_refine_datasets(self.proj, "PrtK-Apo9_1,PrtK-JBS-G8a_1", "dimple")

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


class TestGetLigfitPdbs(_FiltersTester):
    """
    test get_ligfit_pdbs() function
    """

    def test_func(self):
        data_sets = [
            "PrtK-Apo14_1",
            "PrtK-JBS-F3a_1",
            "PrtK-JBS-G8a_1",
            "PrtK-JBS-D12a_1",
        ]

        #
        # get the PDBs
        #
        res = get_ligfit_pdbs(self.proj, data_sets)

        # convert the returned absolute PDB paths to paths
        # relative to project's results dir,
        # to make it easier to compare to expected set of paths
        res_dir = project_results_dir(self.proj)

        relative_res = set()
        for dset, pdb in res:
            rel_pdb = str(Path(pdb).relative_to(res_dir))
            relative_res.add((dset, rel_pdb))

        # check that we got expected dataset and PDB tupels
        self.assertSetEqual(
            relative_res,
            {
                ("PrtK-Apo14_1", "PrtK-Apo14_1/dials/fspipeline/final.pdb"),
                ("PrtK-Apo14_1", "PrtK-Apo14_1/dials/dimple/final.pdb"),
                ("PrtK-Apo14_1", "PrtK-Apo14_1/xdsapp/dimple/final.pdb"),
                ("PrtK-JBS-F3a_1", "PrtK-JBS-F3a_1/autoproc/dimple/final.pdb"),
                ("PrtK-JBS-F3a_1", "PrtK-JBS-F3a_1/dials/dimple/final.pdb"),
            },
        )
