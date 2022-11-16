from pathlib import Path
from projects.database import db_session
from tests.utils import ProjectTestCase, ViewTesterMixin

TEXT_LOG = "log.txt"
HTML_LOG = "log.html"
TEXT_LOG_BODY = b"the front fell off"


class TestLogs(ProjectTestCase, ViewTesterMixin):
    """
    test 'show' and 'download' logs views
    """

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

        #
        # create dummy log files
        #
        self.text_log = Path(self.project.logs_dir, TEXT_LOG)
        self.text_log.write_bytes(TEXT_LOG_BODY)

        self.html_log = Path(self.project.logs_dir, HTML_LOG)
        self.html_log.touch()

    def tearDown(self):
        self.tear_down_temp_dir()

    @db_session
    def test_show_not_found(self):
        """
        case when we are requested to show a log that does not exist
        on the file system
        """
        resp = self.client.get("/logs/show/Foo")
        self.assert_not_found_response(resp, "log file 'Foo' not found")

    @db_session
    def test_download_not_found(self):
        """
        case when a request to download a log that does not exist
        on the file system
        """
        resp = self.client.get("/logs/download/Foo")
        self.assert_not_found_response(resp, "log file 'Foo' not found")

    @db_session
    def test_show_html_log(self):
        """
        show an HTML log
        """
        resp = self.client.get(f"/logs/show/{HTML_LOG}")

        self.assertEqual(resp.status_code, 200)
        self.assert_contains_template(resp, "html_log.html")
        self.assertEqual(resp.context["html_url"], "/logs/htmldata/log.html")

    @db_session
    def test_show_text_log(self):
        """
        show an text log
        """
        resp = self.client.get(f"/logs/show/{TEXT_LOG}")

        self.assertEqual(resp.status_code, 200)
        self.assert_contains_template(resp, "text_log.html")

        self.assertEqual(resp.context["log_text"], TEXT_LOG_BODY.decode())
        self.assertEqual(resp.context["log_path"], self.text_log)
        self.assertEqual(resp.context["download_url"], f"/logs/download/{TEXT_LOG}")

    @db_session
    def test_download(self):
        """
        test downloading a log
        """
        resp = self.client.get(f"/logs/download/{TEXT_LOG}")

        self.assert_response_equals(
            resp, 200, TEXT_LOG_BODY, "application/octet-stream"
        )
