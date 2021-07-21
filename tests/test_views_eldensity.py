from pathlib import Path
from django.urls import reverse
from projects.database import db_session
from tests.utils import ProjectTestCase, ViewTesterMixin
from tests.project_setup import Project, Crystal, DataSet, Result


class TestMapView(ProjectTestCase, ViewTesterMixin):
    MTZ_DATA = b"dummy-mtz-body"

    PROJECTS = [
        Project(
            proposal="20190242",
            protein="Prtk",
            encrypted=False,
            crystals=[Crystal("X01", "VTL", "VT0")],
            datasets=[DataSet("X01", 1)],
            results=[
                Result(dataset=("X01", 1), tool="edna", input_tool=None, result="ok"),
                Result(
                    dataset=("X01", 1), tool="dimple", input_tool="edna", result="ok"
                ),
            ],
        )
    ]

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    def create_dummy_mtz(self, result_dir: Path):
        mtz_file = Path(result_dir, "final.mtz")
        mtz_file.parent.mkdir(parents=True)
        mtz_file.write_bytes(self.MTZ_DATA)

    @db_session
    def test_mtz(self):
        """
        test the URL for fetching MTZ-style density maps
        """

        # set-up mocked MTZ density file
        refine_result = self.project.get_refine_results().first()
        self.create_dummy_mtz(self.project.get_refine_result_dir(refine_result))

        # get the MTZ density file
        url = reverse("density_map", args=(refine_result.id, "mtz"))
        resp = self.client.get(url)

        # check that we got expected response
        self.assert_file_response(resp, self.MTZ_DATA)
