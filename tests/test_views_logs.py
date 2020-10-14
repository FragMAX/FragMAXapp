import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from django.test import TestCase
from tests.utils import ViewTesterMixin

TEXT_LOG = "log.txt"
HTML_LOG = "log.html"
TEXT_LOG_BODY = "the front fell off"


class TestLogs(TestCase, ViewTesterMixin):
    """
    test 'show' and 'download' logs views
    """

    def setUp(self):
        self.setup_client()
        self.setup_project()

        self.temp_dir = tempfile.mkdtemp()
        self.mock_data_path = Mock(return_value=self.temp_dir)

        #
        # create dummy log files
        #
        self.text_log = Path(self.temp_dir, TEXT_LOG)
        with self.text_log.open("w") as f:
            f.write(TEXT_LOG_BODY)

        self.html_log = Path(self.temp_dir, HTML_LOG)
        self.html_log.touch()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_show_not_found(self):
        """
        case when we are requested to show a log that does not exist
        on the file system
        """
        with patch("fragview.models.Project.data_path", self.mock_data_path):
            resp = self.client.get("/logs/show/Foo")

        self.assert_not_found_response(resp, "log file 'Foo' not found")

    def test_download_not_found(self):
        """
        case when a request to download a log that does not exist
        on the file system
        """
        with patch("fragview.models.Project.data_path", self.mock_data_path):
            resp = self.client.get("/logs/download/Foo")

        self.assert_not_found_response(resp, "log file 'Foo' not found")

    def test_show_html_log(self):
        """
        show an HTML log
        """
        with patch("fragview.models.Project.data_path", self.mock_data_path):
            resp = self.client.get(f"/logs/show/{HTML_LOG}")

        self.assertEqual(resp.status_code, 200)
        self.assert_contains_template(resp, "fragview/html_log.html")
        self.assertEqual(resp.context["reportHTML"], str(self.html_log))

    def test_show_text_log(self):
        """
        show an text log
        """
        with patch("fragview.models.Project.data_path", self.mock_data_path):
            resp = self.client.get(f"/logs/show/{TEXT_LOG}")

        self.assertEqual(resp.status_code, 200)
        self.assert_contains_template(resp, "fragview/text_log.html")

        self.assertEqual(resp.context["log_text"], TEXT_LOG_BODY)
        self.assertEqual(resp.context["log_path"], self.text_log)
        self.assertEqual(resp.context["download_url"], f"/logs/download/{TEXT_LOG}")

    def test_download(self):
        """
        test downloading a log
        """
        with patch("fragview.models.Project.data_path", self.mock_data_path):
            resp = self.client.get(f"/logs/download/{TEXT_LOG}")

        self.assert_response(resp, 200, TEXT_LOG_BODY)
        self.assertEqual(resp["Content-Type"], "application/octet-stream")
