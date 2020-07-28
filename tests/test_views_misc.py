import io
from unittest.mock import patch
from os import path
from django import test
from django.urls import reverse
from django.conf import settings
from tests.utils import ViewTesterMixin


class TestLogViewer(test.TestCase, ViewTesterMixin):
    SHIFT = "30000101"
    LOG = "dummy.log"
    LOG_DATA = "something\nsome other thing"

    def setUp(self):
        self.setup_client()
        self.setup_project()
        self.log_path = path.join(settings.PROPOSALS_DIR, self.PROP1, self.SHIFT, self.LOG)

    @patch("os.path.exists")
    def test_no_log(self, exists_mock):

        # mock scenario where log file is does not exists on the file system
        exists_mock.return_value = False
        resp = self.client.get(reverse("log_viewer"), dict(logFile=self.log_path))

        # check created template context
        ctx = resp.context

        self.assertEqual(self.log_path, ctx["dataset"])
        self.assertEqual("", ctx["log"])
        # self.assertEqual("", ctx["downloadPath"])

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_log_found(self, open_mock, exists_mock):

        # mock log file on the file system
        exists_mock.return_value = True
        open_mock.return_value.__enter__.return_value = io.StringIO(self.LOG_DATA)

        resp = self.client.get(reverse("log_viewer"), dict(logFile=self.log_path))

        # check created template context
        ctx = resp.context

        self.assertEqual(self.log_path, ctx["dataset"])
        self.assertEqual(self.LOG_DATA, ctx["log"])
        self.assertEqual("", path.join("/static/biomax", self.PROP1, self.SHIFT, self.LOG), ctx["downloadPath"])
