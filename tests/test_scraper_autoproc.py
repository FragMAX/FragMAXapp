import shutil
from pathlib import Path
from unittest.mock import patch
from fragview.scraper import ToolStatus
from fragview.scraper.autoproc import scrape_results
from projects.database import db_session
from tests.utils import ProjectTestCase, data_file_path
from tests.project_setup import Project as ProjectDesc, Crystal, DataSet


class TestScrapeAutoProc(ProjectTestCase):
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
            self.data_root_dir = Path(self.temp_dir, self.project.proposal)

    def _setup_autoproc_dir(self, dataset, copy_cif=True, copy_mtz=True):
        autoproc_dir = Path(
            self.project.get_dataset_root_dir(dataset),
            "process",
            self.project.protein,
            f"{dataset.crystal.id}",
            f"xds_{dataset.name}_1",
            "autoPROC",
            "cn73_20230326-014102",
            "AutoPROCv1_0_noanom",
        )

        autoproc_dir.mkdir(parents=True)

        # create (empty) summary.html
        Path(autoproc_dir, "summary.html").touch()

        if copy_cif:
            # copy CIF file
            shutil.copy(
                data_file_path("Data_2_autoPROC_TRUNCATE_all.cif"), autoproc_dir
            )

        if copy_mtz:
            #  copy MTZ file
            hdf5_dir = Path(autoproc_dir, "HDF5_1")
            hdf5_dir.mkdir()
            shutil.copy(data_file_path("staraniso_alldata.mtz"), hdf5_dir)

    @db_session
    def test_success(self):
        """
        case when dataset was successfully processed
        """
        dataset = self.project.get_dataset(1)

        with patch("fragview.projects.Project.proposal_dir", self.data_root_dir):
            self._setup_autoproc_dir(dataset)

            res = scrape_results(self.project, dataset)

            self.assertEquals(res.tool, "autoproc")
            self.assertEquals(res.status, ToolStatus.SUCCESS)
            self.assertEquals(res.space_group, "P 41 21 2")
            self.assertEquals(res.unique_reflections, "145993")
            self.assertEquals(res.reflections, "3763099")
            self.assertEquals(res.low_resolution_overall, "65.077")
            self.assertEquals(res.low_resolution_inner, "65.077")
            self.assertEquals(res.low_resolution_out, "1.158")
            self.assertEquals(res.high_resolution_overall, "1.139")
            self.assertEquals(res.high_resolution_inner, "3.091")
            self.assertEquals(res.high_resolution_out, "1.139")
            self.assertAlmostEqual(res.unit_cell_a, 72.053)
            self.assertAlmostEqual(res.unit_cell_b, 72.053)
            self.assertAlmostEqual(res.unit_cell_c, 151.609)
            self.assertAlmostEqual(res.unit_cell_alpha, 90.0)
            self.assertAlmostEqual(res.unit_cell_beta, 90.0)
            self.assertAlmostEqual(res.unit_cell_gamma, 90.0)
            self.assertEquals(res.multiplicity, "25.78")
            self.assertEquals(res.i_sig_average, "16.48")
            self.assertEquals(res.i_sig_out, "0.72")
            self.assertEquals(res.r_meas_average, "0.0917")
            self.assertEquals(res.r_meas_out, "5.1245")
            self.assertEquals(res.completeness_average, "100.0")
            self.assertEquals(res.completeness_out, "100.0")
            self.assertEquals(res.mosaicity, None)
            self.assertEquals(res.isa, None)

    @db_session
    def test_no_result(self):
        """
        the case when autoPROC have not been run for a dataset
        """
        res = scrape_results(self.project, self.project.get_dataset(1))
        self.assertIsNone(res)

    @db_session
    def test_failure_no_cif(self):
        """
        case when no CIF file was generated
        """
        dataset = self.project.get_dataset(1)

        with patch("fragview.projects.Project.proposal_dir", self.data_root_dir):
            self._setup_autoproc_dir(dataset, copy_cif=False)

            res = scrape_results(self.project, dataset)

            self.assertEquals(res.tool, "autoproc")
            self.assertEquals(res.status, ToolStatus.FAILURE)

    @db_session
    def test_failure_no_mtz(self):
        """
        case when no CIF file was generated
        """
        dataset = self.project.get_dataset(1)

        with patch("fragview.projects.Project.proposal_dir", self.data_root_dir):
            self._setup_autoproc_dir(dataset, copy_mtz=False)

            res = scrape_results(self.project, dataset)

            self.assertEquals(res.tool, "autoproc")
            self.assertEquals(res.status, ToolStatus.FAILURE)
