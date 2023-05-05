from tests.utils import ViewTesterMixin, ProjectTestCase
from projects.database import db_session
from tests.project_setup import Project, DataSet, Crystal, Result
from fragview.views.wrap import DatasetInfo, ProcessingInfo

PROJECTS = [
    Project(
        protein="MID2",
        proposal="20180453",
        crystals=[
            Crystal("MID2-x01", "TstLib", "VT0"),
            Crystal("MID2-x02", "TstLib", "VT0"),
            Crystal("MID2-x03", "TstLib", "VT0"),
        ],
        datasets=[
            DataSet("MID2-x01", 1),
            DataSet("MID2-x02", 1),
            DataSet("MID2-x02", 2),
            DataSet("MID2-x03", 1),
        ],
        results=[
            Result(dataset=("MID2-x01", 1), tool="edna", input_tool=None, result="ok"),
            Result(dataset=("MID2-x02", 1), tool="xds", input_tool=None, result="ok"),
            Result(
                dataset=("MID2-x03", 1), tool="xdsapp", input_tool=None, result="error"
            ),
        ],
    ),
]


class TestProcessView(ProjectTestCase, ViewTesterMixin):
    PROJECTS = PROJECTS

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    def _assert_dataset_info(
        self,
        dset: DatasetInfo,
        name: str,
        xds_result,
        edna_result,
        xdsapp_result,
        processed: bool,
    ):
        self.assertEqual(dset.name, name)
        self.assertEqual(dset.xds_result(), xds_result)
        self.assertEqual(dset.edna_result(), edna_result)
        self.assertEqual(dset.xdsapp_result(), xdsapp_result)
        self.assertEqual(dset.processed(), processed)

    @db_session
    def test_view(self):
        resp = self.client.get("/analysis/process")

        self.assertEquals(resp.status_code, 200)

        # check template used
        self.assert_contains_template(resp, "analysis_process.html")

        #
        # check created template context
        #
        ctx = resp.context

        dsets = ctx["datasets"]
        self.assertEqual(len(dsets), 4)
        self._assert_dataset_info(dsets[0], "MID2-x01_1", None, "ok", None, True)
        self._assert_dataset_info(dsets[1], "MID2-x02_1", "ok", None, None, True)
        self._assert_dataset_info(dsets[2], "MID2-x02_2", None, None, None, False)
        self._assert_dataset_info(dsets[3], "MID2-x03_1", None, None, "error", True)

        # smoke test on pipelines, check that some proc tools are returned
        pipelines = ctx["pipelines"]
        self.assertTrue("xia2_xds" in pipelines)
        self.assertTrue("xia2_dials" in pipelines)

        # smoke test on space groups, check that it appears
        # that 8 space group systems are listed
        space_groups = ctx["space_group_systems"]
        self.assertEqual(len(space_groups), 8)


class TestRefineView(ProjectTestCase, ViewTesterMixin):
    PROJECTS = PROJECTS

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    def _assert_proc_info(
        self,
        proc_info: ProcessingInfo,
        dataset_name: str,
        tool_name: str,
        space_group_hm: str,
    ):
        self.assertEqual(proc_info.dataset.name, dataset_name)
        self.assertEqual(proc_info.tool_name(), tool_name)
        self.assertEqual(proc_info.space_group.hm, space_group_hm)

    @db_session
    def test_view(self):
        resp = self.client.get("/analysis/refine")

        self.assertEquals(resp.status_code, 200)

        # check template used
        self.assert_contains_template(resp, "analysis_refine.html")

        #
        # check created template context
        #
        ctx = resp.context

        proc_results = ctx["proc_results"]
        self.assertEqual(len(proc_results), 2)

        self._assert_proc_info(proc_results[0], "MID2-x01_1", "edna", "C 2 2 2")
        self._assert_proc_info(proc_results[1], "MID2-x02_1", "XIA2/XDS", "C 2 2 2")
