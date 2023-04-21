import shutil
from pathlib import Path
from tests.utils import ProjectTestCase, data_file_path
from tests.project_setup import Project, Crystal, DataSet
from gemmi import UnitCell
from fragview.scraper import RefineResult, ToolStatus
from fragview.scraper.fspipeline import scrape_results
from projects.database import db_session


class TestScrapeResults(ProjectTestCase):
    """
    test scrape_results()
    """

    PROJECTS = [
        Project(
            proposal="20190242",
            protein="TRIM2",
            crystals=[
                Crystal("TRIM2-x0010", None, None),  # Apo crystal
            ],
            datasets=[
                DataSet("TRIM2-x0010", 1),
            ],
            results=[],
        )
    ]

    def setup_result_dir(self, dataset, pdb_file: str):
        res_dir = self.project.get_dataset_results_dir(dataset)

        # copy the pdb file to results directory
        dest_pdb = Path(res_dir, "xdsapp", "fspipeline", "final.pdb")
        src_pdb = data_file_path(pdb_file)
        dest_pdb.parent.mkdir(parents=True)
        shutil.copy(src_pdb, dest_pdb)

        # copy the blobs file to results directory
        dest_blobs = Path(res_dir, "xdsapp", "fspipeline", "blobs.log")
        src_blobs = data_file_path("blobs.log")
        shutil.copy(src_blobs, dest_blobs)

    def assert_result(self, first, second):
        self.assertEqual(first.proc_tool, second.proc_tool)
        self.assertEqual(first.refine_tool, second.refine_tool)
        self.assertEqual(first.status, second.status)
        self.assertEqual(first.space_group, second.space_group)
        self.assertAlmostEqual(first.resolution, second.resolution)
        self.assertEqual(first.r_work, second.r_work)
        self.assertEqual(first.r_free, second.r_free)
        self.assertEqual(first.rms_bonds, second.rms_bonds)
        self.assertEqual(first.rms_angles, second.rms_angles)
        self.assertAlmostEqual(first.cell.a, second.cell.a)
        self.assertAlmostEqual(first.cell.b, second.cell.b)
        self.assertAlmostEqual(first.cell.c, second.cell.c)
        self.assertAlmostEqual(first.cell.alpha, second.cell.alpha)
        self.assertAlmostEqual(first.cell.beta, second.cell.beta)
        self.assertAlmostEqual(first.cell.gamma, second.cell.gamma)
        self.assertEqual(first.blobs, second.blobs)

    def assert_results(self, first: list[RefineResult], second: list[RefineResult]):
        self.assertEqual(len(first), len(second))
        for res1, res2 in zip(first, second):
            self.assert_result(res1, res2)

    @db_session
    def test_phenix_v17_ok(self):
        """
        test scraping results of successful processing with
        fspipeline using phenix package version 1.17.*
        """
        dataset = self.project.get_datasets().first()

        self.setup_result_dir(dataset, "fspipe_phenix_v17.pdb")

        results = list(scrape_results(self.project, dataset))
        expected = RefineResult("xdsapp", "fspipeline")
        expected.status = ToolStatus.SUCCESS
        expected.space_group = "C121"
        expected.resolution = 2.19
        expected.r_work = "0.2303"
        expected.r_free = "0.3489"
        expected.rms_bonds = "0.018"
        expected.rms_angles = "1.646"
        expected.cell = UnitCell(76.783, 64.132, 39.409, 90, 116.41, 90)
        expected.blobs = (
            "[[-8.66, -40.27, 59.35], "
            "[46.38, -52.1, 50.19], "
            "[-9.753, -17.56, 47.49], "
            "[-5.67, -31.23, 7.807], "
            "[-6.521, 22.47, 33.3]]"
        )

        self.assert_results(results, [expected])

    @db_session
    def test_phenix_v19_ok(self):
        """
        test scraping results of successful processing with
        fspipeline using phenix package version 1.19.*
        """
        dataset = self.project.get_datasets().first()

        self.setup_result_dir(dataset, "fspipe_phenix_v19.pdb")

        results = list(scrape_results(self.project, dataset))
        expected = RefineResult("xdsapp", "fspipeline")
        expected.status = ToolStatus.SUCCESS
        expected.space_group = "C121"
        expected.resolution = 3.01
        expected.r_work = "0.2212"
        expected.r_free = "0.3966"
        expected.rms_bonds = "0.016"
        expected.rms_angles = "1.488"
        expected.cell = UnitCell(112.41, 56.73, 83.22, 90, 102.18, 90)
        expected.blobs = (
            "[[-8.66, -40.27, 59.35], "
            "[46.38, -52.1, 50.19], "
            "[-9.753, -17.56, 47.49], "
            "[-5.67, -31.23, 7.807], "
            "[-6.521, 22.47, 33.3]]"
        )

        self.assert_results(results, [expected])
