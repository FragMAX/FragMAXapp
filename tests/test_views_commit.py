from unittest import TestCase
from unittest.mock import patch
from django.urls import reverse
from tests.utils import ViewTesterMixin

TEST_COMMIT_DESC = "0cafe00 (tag: maxiv_r99) fixed them all"


class TestCommit(TestCase, ViewTesterMixin):
    def setUp(self):
        self.setup_client()
        self.setup_project()

    @patch("pathlib.Path.is_file")
    @patch("pathlib.Path.read_text")
    def test_known(self, mock_read_text, mock_is_file):

        mock_read_text.return_value = TEST_COMMIT_DESC
        mock_is_file.return_value = True

        resp = self.client.get(reverse("commit"))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/plain")
        self.assertEqual(resp.content.decode(), TEST_COMMIT_DESC)

    @patch("pathlib.Path.is_file")
    def test_unspecified(self, mock_is_file):
        mock_is_file.return_value = False

        resp = self.client.get(reverse("commit"))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/plain")
        self.assertEqual(resp.content.decode(), "unspecified")
