from os import path
import unittest
from unittest.mock import ANY
import shutil
import tempfile
from fragview import auth
from django import test
from fragview.models import Project, Library


def identity(func):
    return func


class WorkerTaskTester(unittest.TestCase):
    def assert_locking(self, red_lock_mock, lock_id):
        """
        make assertions that a RedLock with specified id was acquired and released
        """
        red_lock_mock.assert_called_once_with(lock_id, [ANY])

        lock = red_lock_mock.return_value
        lock.acquire.assert_called_once_with()
        lock.release.assert_called_once_with()


class ViewTesterMixin:
    """
    Utility mixin, that provides method to setup authenticated HTTP client
    """

    PROP1 = "20180201"
    PROP2 = "20170223"

    def setup_client(self):
        """
        setup test HTTP client which is logged in with a user 'dummy'
        that have access to PROP1 and PROP2 proposals
        """
        self.user = auth.ISPyBBackend()._get_user_obj("dummy")
        self.client = test.Client()
        self.client.force_login(user=self.user)

        session = self.client.session
        session["proposals"] = [self.PROP1, self.PROP2]
        session.save()

    def setup_project(self, encrypted=False):
        self.lib = Library(name="JBS")
        self.lib.save()

        self.proj = Project(
            protein="PRT",
            library=self.lib,
            proposal=self.PROP1,
            shift="20190808",
            encrypted=encrypted,
        )
        self.proj.save()

    def assert_contains_template(self, response, template_name):
        """
        assert that the response rendering involved using the specified template
        """
        templ_names = [t.name for t in response.templates]
        self.assertIn(template_name, templ_names)

    def assert_response(self, response, status_code, content_regexp):
        self.assertEquals(response.status_code, status_code)
        self.assertRegex(response.content.decode(), content_regexp)

    def assert_response_equals(self, response, status_code, content, content_type):
        """
        assert exact match of responses's status code, content body and content-type header
        """
        self.assertEquals(response.status_code, status_code)
        self.assertEquals(response.content, content)
        self.assertEquals(response["content-type"], content_type)

    def assert_bad_request(self, response, error_msg):
        self.assert_response(response, 400, error_msg)

    def assert_not_found_response(self, response, error_msg):
        self.assert_response(response, 404, error_msg)


class TempDirMixin:
    def setup_temp_dir(self):
        self.temp_dir = tempfile.mkdtemp()

    def tear_down_temp_dir(self):
        shutil.rmtree(self.temp_dir)


def data_file_path(file_name):
    """
    return absolute path specified file in tests 'data' directory
    """
    return path.join(path.dirname(__file__), "data", file_name)


def xs_data_path(num):
    return data_file_path(f"xs_data{num}.xml")
