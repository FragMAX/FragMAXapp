from typing import List, Tuple, Set, Iterable
from pathlib import Path
from django.test import TestCase
from projects.database import db_session
from fragview.filters import get_proc_datasets, get_refine_datasets, get_ligfit_datasets
from tests.utils import TempDirMixin
from tests.project_setup import create_temp_project, Project, Crystal, DataSet, Result


PROJECT = Project(
    protein="Nsp12",
    proposal="20301299",
    encrypted=False,
    crystals=[
        Crystal("X01", "VTL", "VT0"),
        Crystal("X02", "FTL", "FL0"),
        Crystal("X03", "FTL", "FL1"),
        Crystal("X04", "FTL", "FL2"),
        Crystal("X05", "FTL", "FL2"),
    ],
    datasets=[
        DataSet("X01", 1),
        DataSet("X01", 2),
        DataSet("X02", 1),
        DataSet("X03", 1),
        DataSet("X04", 1),
        DataSet("X05", 1),
    ],
    results=[
        Result(dataset=("X01", 1), tool="edna", input_tool=None, result="ok"),
        Result(dataset=("X02", 1), tool="edna", input_tool=None, result="ok"),
        Result(dataset=("X03", 1), tool="dimple", input_tool=None, result="ok"),
        Result(dataset=("X03", 1), tool="rhofit", input_tool=None, result="ok"),
        Result(dataset=("X04", 1), tool="ligandfit", input_tool=None, result="ok"),
    ],
)


class _FilterTestCase(TestCase, TempDirMixin):
    ALL_DATASETS = [
        DataSet("X01", 1),
        DataSet("X01", 2),
        DataSet("X02", 1),
        DataSet("X03", 1),
        DataSet("X04", 1),
        DataSet("X05", 1),
    ]

    def setUp(self):
        self.setup_temp_dir()

        projects_db_dir = Path(self.temp_dir, "db", "projs")

        # override path to projects database dir
        self.settings_override = self.settings(
            PROJECTS_DB_DIR=projects_db_dir,
        )
        self.settings_override.enable()

        self.project = create_temp_project(projects_db_dir, PROJECT)

    def tearDown(self):
        self.tear_down_temp_dir()

    def assert_datasets(self, expected: List[DataSet], got):
        got_list = []
        for dataset in got:
            got_list.append(DataSet(dataset.crystal.id, dataset.run))

        self.assertListEqual(expected, got_list)

    def get_dataset_ids(self, first: int, last: int) -> Tuple[Set[str], str]:
        datasets = self.project.get_datasets()
        ids = {str(dataset.id) for dataset in datasets[first:last]}
        ids_string = ",".join(ids)

        return ids, ids_string

    def as_dataset_ids(self, datasets: Iterable) -> Set[str]:
        return {str(dataset.id) for dataset in datasets}


class TestGetProcDatasets(_FilterTestCase):
    """
    test get_proc_datasets(), the dataset filtering for 'data processing' jobs
    """

    NEW_DATASET = [
        DataSet("X01", 2),
        DataSet("X03", 1),
        DataSet("X04", 1),
        DataSet("X05", 1),
    ]

    @db_session
    def test_all(self):
        """
        test the 'ALL' filter
        """
        datasets = get_proc_datasets(self.project, "ALL", None)
        self.assert_datasets(self.ALL_DATASETS, datasets)

    @db_session
    def test_new(self):
        """
        test 'NEW' filter
        """
        datasets = get_proc_datasets(self.project, "NEW", "edna")
        self.assert_datasets(self.NEW_DATASET, datasets)

    @db_session
    def test_selected(self):
        """
        test the filter where datasets are explicitly specified
        """
        ids, ids_string = self.get_dataset_ids(0, 3)

        datasets = get_proc_datasets(self.project, ids_string, None)
        got_ids = self.as_dataset_ids(datasets)

        self.assertSetEqual(ids, got_ids)


class TestGetRefineDatasets(_FilterTestCase):
    """
    test get_refine_datasets()
    """

    NEW_DATASET = [
        DataSet("X01", 1),
        DataSet("X01", 2),
        DataSet("X02", 1),
        DataSet("X04", 1),
        DataSet("X05", 1),
    ]

    @db_session
    def test_all(self):
        """
        test the 'ALL' filter
        """
        datasets = get_refine_datasets(self.project, "ALL", None)
        self.assert_datasets(self.ALL_DATASETS, datasets)

    @db_session
    def test_new_dimple(self):
        """
        test 'NEW' filter, with dimple selected
        """
        datasets = get_refine_datasets(self.project, "NEW", "dimple")
        self.assert_datasets(self.NEW_DATASET, datasets)

    @db_session
    def test_selected(self):
        """
        test the filter where datasets are explicitly specified
        """
        ids, ids_string = self.get_dataset_ids(1, 4)

        datasets = get_refine_datasets(self.project, ids_string, None)
        got_ids = self.as_dataset_ids(datasets)

        self.assertSetEqual(ids, got_ids)


class TestGetLigfitDatasets(_FilterTestCase):
    """
    test get_ligfit_datasets()
    """

    NEW_LIGANDFIT_DATASET = [
        DataSet("X01", 1),
        DataSet("X01", 2),
        DataSet("X02", 1),
        DataSet("X03", 1),
        DataSet("X05", 1),
    ]

    NEW_RHOFIT_DATASET = [
        DataSet("X01", 1),
        DataSet("X01", 2),
        DataSet("X02", 1),
        DataSet("X04", 1),
        DataSet("X05", 1),
    ]

    @db_session
    def test_all(self):
        """
        test the 'ALL' filter
        """
        datasets = get_ligfit_datasets(self.project, "ALL", None)
        self.assert_datasets(self.ALL_DATASETS, datasets)

    @db_session
    def test_new_ligandfit(self):
        """
        test 'NEW' filter with ligandfit selected
        """
        datasets = get_ligfit_datasets(self.project, "NEW", "ligandfit")
        self.assert_datasets(self.NEW_LIGANDFIT_DATASET, datasets)

    @db_session
    def test_new_rho_fit(self):
        """
        test 'NEW' filter with rho_fit selected
        """
        datasets = get_ligfit_datasets(self.project, "NEW", "rhofit")
        self.assert_datasets(self.NEW_RHOFIT_DATASET, datasets)

    @db_session
    def test_selected(self):
        """
        test the filter where datasets are explicitly specified
        """
        ids, ids_string = self.get_dataset_ids(1, 4)

        datasets = get_ligfit_datasets(self.project, ids_string, None)
        got_ids = self.as_dataset_ids(datasets)

        self.assertSetEqual(ids, got_ids)
