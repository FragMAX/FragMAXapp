from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from tests.utils import ViewTesterMixin
from fragview.models import PDB
from fragview.sites.plugin import Pipeline, LigandTool

PIPELINES = {Pipeline.BUSTER, Pipeline.XIA2_XDS}
DEF_LIGAND_TOOL = LigandTool.ACEDRG
LIGAND_TOOLS = {LigandTool.ACEDRG, LigandTool.ELBOW}


class MockSitePlugin:
    PROPOSALS_DIR = "/foo"

    def get_supported_pipelines(self):
        return PIPELINES

    def get_supported_ligand_tools(self):
        return DEF_LIGAND_TOOL, LIGAND_TOOLS

    def get_project_datasets(self, project):
        return ["Foo-Lib-A0_1", "hCAII-Apo25_1", "Foo-Lib-B0_2"]


class TestProcessingForm(TestCase, ViewTesterMixin):
    def setUp(self):
        self.setup_client()
        self.setup_project()

        # add PDB to our project
        self.pdb = PDB(project=self.proj, filename="moin.pdb")
        self.pdb.save()

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
        self.assert_contains_template(resp, "fragview/data_analysis.html")

        # check created template context
        ctx = resp.context

        self.assertEqual(
            ctx["datasets"], ["Foo-Lib-A0_1", "Foo-Lib-B0_2", "hCAII-Apo25_1"]
        )
        self.assertEqual(list(ctx["pdbs"]), [self.pdb])
        self.assertEqual(ctx["methods"], [])
        self.assertEqual(ctx["pipelines"], PIPELINES)
        self.assertEqual(ctx["default_ligand_tool"], DEF_LIGAND_TOOL)
        self.assertEqual(ctx["ligand_tools"], LIGAND_TOOLS)
