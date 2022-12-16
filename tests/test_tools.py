from fragview.sites.plugin import BatchFile
from fragview.tools import generate_process_batch, Tool, ProcessOptions
from fragview.projects import Project
from projects.database import db_session
from tests.utils import ProjectTestCase
from tests.project_setup import Crystal, DataSet
from tests.project_setup import Project as ProjectDesc


class TestGenerateProcessBatch(ProjectTestCase):
    """
    simple smoke tests on generating batch script for data processing tools
    """

    PROJECTS = [
        ProjectDesc(
            proposal="20190242",
            protein="Prtk",
            crystals=[Crystal("X01", "VTL", "VT0")],
            datasets=[DataSet("X01", 1)],
            results=[],
        )
    ]

    def _assert_batch(
        self,
        project: Project,
        batch: BatchFile,
        filename_regexp: str,
        body_regexp: str,
    ):
        # smoke tests on file name
        self.assertTrue(batch._filename.startswith(str(project.scripts_dir)))
        self.assertRegex(batch._filename, filename_regexp)

        # smoke test on script body
        self.assertRegex(batch._body, body_regexp)

    @db_session
    def test_xdsapp(self):
        dataset = self.project.get_dataset(1)
        options = ProcessOptions(None, None)
        batch = generate_process_batch(Tool.XDSAPP, self.project, dataset, options)

        self._assert_batch(self.project, batch, "xdsapp.*sh", "xdsapp")

    @db_session
    def test_xds(self):
        dataset = self.project.get_dataset(1)
        options = ProcessOptions(None, None)
        batch = generate_process_batch(Tool.XDS, self.project, dataset, options)

        self._assert_batch(self.project, batch, "xds.*sh", r"xia2.*pipeline\=3dii")

    @db_session
    def test_dials(self):
        dataset = self.project.get_dataset(1)
        options = ProcessOptions(None, None)
        batch = generate_process_batch(Tool.DIALS, self.project, dataset, options)

        self._assert_batch(self.project, batch, "dials.*sh", r"xia2.*pipeline\=dials")
