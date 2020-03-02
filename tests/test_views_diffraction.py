from os import path
from unittest.mock import patch
from django import test
from django.urls import reverse
from fragview.models import Project
from fragview.projects import project_raw_protein_dir, project_process_protein_dir, project_static_url
from tests.utils import ViewTesterMixin

SHIFT = "20180101"
DATA_SET = "PrtN-Apo0"
RUN = 1


class TestImage(test.TestCase, ViewTesterMixin):
    def setUp(self):
        self.setup_client()

        self.proj = Project(protein="PrtN", library="Lbr", proposal=self.PROP1, shift=SHIFT)
        self.proj.save()

        self.url = reverse("diffraction_image", args=[DATA_SET, RUN, 0])

    def test_image_ok(self):
        """
        test the happy path for generating diffraction picture from H5 file
        """
        expected_h5_path = path.join(project_raw_protein_dir(self.proj), DATA_SET,
                                     f"{DATA_SET}_{RUN}_data_000000.h5")

        expected_jpeg_path = path.join(project_process_protein_dir(self.proj), DATA_SET,
                                       f"diffraction_{RUN}_000000.jpeg")

        expected_url = path.join(project_static_url(self.proj), "fragmax", "process",
                                 self.proj.protein, DATA_SET, f"diffraction_{RUN}_000000.jpeg")

        # mock the celery task invocation and files systems access
        with patch("fragview.views.diffraction.get_diffraction") as get_diff_mock:
            with patch("os.path.isfile") as isfile_mock:
                isfile_mock.return_value = True

                resp = self.client.get(self.url)

                # check that task was invoked on correct H5 and JPEG paths
                get_diff_mock.delay.assert_called_with(expected_h5_path, expected_jpeg_path)
                isfile_mock.assert_called_with(expected_h5_path)

                # check that we got redirected to the generated jpeg
                self.assertRedirects(resp, expected_url, fetch_redirect_response=False)

    def test_image_no_found(self):
        """
        test the case when H5 for specified dataset does not exist
        """
        with patch("os.path.isfile") as isfile_mock:
            isfile_mock.return_value = False
            resp = self.client.get(self.url)
            self.assertContains(resp, "H5 file found", status_code=404)
