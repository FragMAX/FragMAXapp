from pathlib import Path
from unittest.mock import patch
from shutil import copy
from fragview.scraper import ToolStatus
from fragview.scraper.edna import scrape_results
from projects.database import db_session
from tests.utils import ProjectTestCase, data_file_path
from tests.project_setup import Project as ProjectDesc, Crystal, DataSet


class TestScrapeEdna(ProjectTestCase):
    PROJECTS = [
        ProjectDesc(
            proposal="20190242",
            protein="Prtk",
            crystals=[Crystal("X01", "VTL", "VT0")],
            datasets=[DataSet("X01", 1)],
            results=[],
        )
    ]

    def setUp(self):
        super().setUp()

        # create 'raw dataset root' directory, inside our temp directory
        with db_session:
            self.data_root_dir = Path(self.temp_dir, "raw", self.project.proposal)

    def _setup_edna_dir(self, dataset, copy_mtz=True, copy_aimless_log=True):
        edna_res_dir = Path(
            self.project.get_dataset_root_dir(dataset),
            "process",
            self.project.protein,
            f"{dataset.crystal.id}",
            f"xds_{dataset.name}_1",
            "EDNA_proc",
            "results",
        )

        edna_res_dir.mkdir(parents=True)

        # copy MTZ file
        if copy_mtz:
            src_mtz = data_file_path("edna_anom_aimless.mtz")
            copy(src_mtz, edna_res_dir)

        # copy aimless log
        if copy_aimless_log:
            src_log = data_file_path("edna_aimless_anom.log")
            dest_log = Path(edna_res_dir, f"ep_{dataset.name}_aimless_anom.log")
            copy(src_log, dest_log)

        # copy XSCALE log
        src_log = data_file_path("edna_XSCALE.LP")
        copy(src_log, edna_res_dir)

    @db_session
    def test_success(self):
        """
        case when dataset was successfully processed
        """
        dataset = self.project.get_dataset(1)

        with patch("fragview.projects.Project.proposal_dir", self.data_root_dir):
            self._setup_edna_dir(dataset)

            res = scrape_results(self.project, dataset)

            self.assertEquals(res.tool, "edna")
            self.assertEquals(res.status, ToolStatus.SUCCESS)
            self.assertEquals(res.space_group, "P 31 2 1")
            self.assertEquals(res.unique_reflections, "148656")
            self.assertEquals(res.reflections, "1649797")
            self.assertEquals(res.low_resolution_overall, "49.92")
            self.assertEquals(res.low_resolution_out, "1.60")
            self.assertEquals(res.high_resolution_overall, "1.55")
            self.assertEquals(res.high_resolution_out, "1.55")
            self.assertAlmostEqual(res.unit_cell_a, 104.707)
            self.assertAlmostEqual(res.unit_cell_b, 104.707)
            self.assertAlmostEqual(res.unit_cell_c, 160.005)
            self.assertAlmostEqual(res.unit_cell_alpha, 90.0)
            self.assertAlmostEqual(res.unit_cell_beta, 90.0)
            self.assertAlmostEqual(res.unit_cell_gamma, 120.0)
            self.assertEquals(res.multiplicity, "11.1")
            self.assertEquals(res.i_sig_average, "19.9")
            self.assertEquals(res.i_sig_out, "1.7")
            self.assertEquals(res.r_meas_average, "0.064")
            self.assertEquals(res.r_meas_out, "1.442")
            self.assertEquals(res.completeness_average, "100.0")
            self.assertEquals(res.completeness_out, "100.0")
            self.assertEquals(res.mosaicity, "0.05")
            self.assertEquals(res.isa, "22.41")

    @db_session
    def test_no_result(self):
        """
        the case when edna have not been run for a dataset
        """
        res = scrape_results(self.project, self.project.get_dataset(1))
        self.assertIsNone(res)

    @db_session
    def test_failure_no_mtz(self):
        """
        case when no MTZ file was generated
        """
        dataset = self.project.get_dataset(1)

        with patch("fragview.projects.Project.proposal_dir", self.data_root_dir):
            self._setup_edna_dir(dataset, copy_mtz=False, copy_aimless_log=False)

            res = scrape_results(self.project, dataset)

            self.assertEquals(res.tool, "edna")
            self.assertEquals(res.status, ToolStatus.FAILURE)

    @db_session
    def test_failure_no_aimless_log(self):
        """
        case when no aimless log was generated
        """
        dataset = self.project.get_dataset(1)

        with patch("fragview.projects.Project.proposal_dir", self.data_root_dir):
            self._setup_edna_dir(dataset, copy_aimless_log=False)

            res = scrape_results(self.project, dataset)

            self.assertEquals(res.tool, "edna")
            self.assertEquals(res.status, ToolStatus.FAILURE)
