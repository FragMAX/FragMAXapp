from unittest.mock import patch
from django.urls import reverse
from tests.utils import ViewTesterMixin, ProjectTestCase
from fragview.sites.plugin import Pipeline, LigandTool
from projects.database import db_session

PIPELINES = {Pipeline.DIMPLE, Pipeline.XIA2_XDS}
DEF_LIGAND_TOOL = LigandTool.ACEDRG
LIGAND_TOOLS = {LigandTool.ACEDRG, LigandTool.ELBOW}


class MockSitePlugin:
    def get_supported_pipelines(self):
        return PIPELINES

    def get_supported_ligand_tools(self):
        return DEF_LIGAND_TOOL, LIGAND_TOOLS


class TestProcessingForm(ProjectTestCase, ViewTesterMixin):
    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    @db_session
    def test_view(self):
        """
        test the 'data analysis' form view
        """
        site = MockSitePlugin()

        with patch("fragview.views.analysis.SITE", site):
            with patch("fragview.projects.SITE", site):
                resp = self.client.get(reverse("data_analysis"))

        self.assertEquals(resp.status_code, 200)

        # check template used
        self.assert_contains_template(resp, "data_analysis.html")

        # check created template context
        ctx = resp.context

        self.assertEqual(ctx["pipelines"], PIPELINES)
        self.assertEqual(ctx["default_ligand_tool"], DEF_LIGAND_TOOL)
        self.assertEqual(ctx["ligand_tools"], LIGAND_TOOLS)
