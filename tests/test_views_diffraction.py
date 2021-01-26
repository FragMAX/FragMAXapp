from os import path
from unittest.mock import patch
from django import test
from django.urls import reverse
from fragview.projects import (
    project_raw_protein_dir,
    project_process_protein_dir,
)
from tests.utils import ViewTesterMixin

SHIFT = "20180101"
DATA_SET = "PrtN-Apo0"
RUN = 1


class TestImage(test.TestCase, ViewTesterMixin):
    def setUp(self):
        self.setup_client()
        self.setup_project()

        self.url = reverse("diffraction_image", args=[DATA_SET, RUN, 0])

    def test_image_ok(self):
        """
        test the happy path for generating diffraction picture from source image file
        """
        expected_h5_path = path.join(
            project_raw_protein_dir(self.proj),
            DATA_SET,
            f"{DATA_SET}_{RUN}_data_000000.h5",
        )

        expected_jpeg_path = path.join(
            project_process_protein_dir(self.proj),
            DATA_SET,
            f"diffraction_{RUN}_000000.jpeg",
        )

        # mock the celery task invocation and TBD
        with patch("fragview.views.diffraction.get_diffraction") as get_diff_mock:
            with patch("os.path.isfile") as isfile_mock:
                with patch("fragview.views.utils.read_proj_file") as read_proj_file:
                    isfile_mock.return_value = True
                    read_proj_file.return_value = b"dummy-jpeg-data"

                    resp = self.client.get(self.url)

                    # check that task was invoked on correct image and JPEG paths
                    get_diff_mock.delay.assert_called_with(
                        expected_h5_path, expected_jpeg_path
                    )
                    isfile_mock.assert_called_with(expected_h5_path)
                    read_proj_file.assert_called_once_with(
                        self.proj, expected_jpeg_path
                    )

                    # check that we got jpeg response
                    self.assert_response_equals(
                        resp, 200, b"dummy-jpeg-data", "image/jpeg"
                    )

    def test_image_not_found(self):
        """
        test the case when H5 for specified dataset does not exist
        """
        with patch("os.path.isfile") as isfile_mock:
            isfile_mock.return_value = False
            resp = self.client.get(self.url)
            self.assertContains(
                resp, "diffraction source file not found", status_code=404
            )
