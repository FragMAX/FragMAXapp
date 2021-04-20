from pathlib import Path
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from tests.utils import ViewTesterMixin, TempDirMixin


class TestMapView(TestCase, ViewTesterMixin, TempDirMixin):
    MTZ_DATA = b"dummy-mtz-body"

    def setUp(self):
        self.setup_client()
        self.setup_project()
        self.setup_temp_dir()

    def tearDown(self):
        self.tear_down_temp_dir()

    def create_dummy_mtz(self, dataset, process, refine):
        mtz_file = Path(self.temp_dir, dataset, process, refine, "final.mtz")
        mtz_file.parent.mkdir(parents=True)
        mtz_file.write_bytes(self.MTZ_DATA)

    @patch("fragview.views.eldensity.project_results_dir")
    def test_mtz(self, project_results_dir_mock):
        """
        test the URL for fetching MTZ-style density maps
        """

        # the dataset, process and refine tools for our test
        dataset = f"{self.proj.protein}-VT02"
        process = "edna"
        refine = "dimple"

        # set-up mocked MTZ density file
        self.create_dummy_mtz(dataset, process, refine)
        project_results_dir_mock.return_value = self.temp_dir

        # get the MTZ density file
        url = reverse("density_map", args=(dataset, process, refine, "mtz"))
        resp = self.client.get(url)

        # check that we got expected response
        self.assert_file_response(resp, self.MTZ_DATA)
